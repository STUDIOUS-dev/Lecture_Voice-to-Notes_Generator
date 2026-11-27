"""
IntelliLecture API.

Serves the REST API under /api and, in production, the built React app
(frontend/dist) from the same origin, so the whole site deploys as a single
service.
"""

import logging
import re
import threading
import time
import uuid
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from backend.config import settings
from backend.jobs import JobStore, utc_now_iso
from backend.pipeline import process_lecture

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
logger = logging.getLogger("intellilecture")

store = JobStore(settings.data_dir)
executor: ThreadPoolExecutor | None = None
_stop_cleanup = threading.Event()


def _cleanup_loop() -> None:
    while not _stop_cleanup.wait(3600):
        try:
            store.cleanup(settings.job_ttl_hours)
        except Exception:  # noqa: BLE001
            logger.exception("Cleanup failed")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global executor
    executor = ThreadPoolExecutor(max_workers=max(1, settings.max_concurrent_jobs),
                                  thread_name_prefix="lecture")
    _stop_cleanup.clear()
    store.mark_interrupted()
    store.cleanup(settings.job_ttl_hours)
    threading.Thread(target=_cleanup_loop, daemon=True, name="cleanup").start()
    logger.info("AI provider: %s", settings.provider_name)
    if settings.ai_provider == "api" and not settings.api_key:
        logger.error("AI_PROVIDER=api but no GROQ_API_KEY / LLM_API_KEY is set")
    yield
    _stop_cleanup.set()
    executor.shutdown(wait=False, cancel_futures=True)


app = FastAPI(title="IntelliLecture API", version="2.0.0", lifespan=lifespan,
              docs_url="/api/docs", openapi_url="/api/openapi.json", redoc_url=None)

app.add_middleware(GZipMiddleware, minimum_size=1024)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    return response


# ── Simple in-memory rate limiter (per client IP) ────────────────────────────
_upload_log: dict[str, deque] = defaultdict(deque)
_rate_lock = threading.Lock()


def _check_rate_limit(ip: str) -> None:
    limit = settings.uploads_per_hour
    if limit <= 0:
        return
    now = time.time()
    with _rate_lock:
        history = _upload_log[ip]
        while history and now - history[0] > 3600:
            history.popleft()
        if len(history) >= limit:
            retry = int(3600 - (now - history[0])) + 1
            raise HTTPException(
                status_code=429,
                detail=f"Upload limit reached ({limit} per hour). Try again in {retry // 60 + 1} minutes.",
                headers={"Retry-After": str(retry)},
            )
        history.append(now)


def _load_job(job_id: str) -> dict:
    job = store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found. It may have expired.")
    return job


def _require_done(job_id: str) -> dict:
    job = _load_job(job_id)
    if job.get("status") != "done":
        raise HTTPException(status_code=409, detail="Job is not complete yet.")
    return job


def _download_headers(original_name: str, suffix: str) -> dict:
    stem = Path(original_name or "lecture").stem or "lecture"
    ascii_name = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("_") or "lecture"
    return {
        "Content-Disposition": (
            f'attachment; filename="{ascii_name}{suffix}"; '
            f"filename*=UTF-8''{quote(stem + suffix)}"
        )
    }


# ── API routes ───────────────────────────────────────────────────────────────
@app.get("/api/health")
def health():
    return {"status": "ok", "provider": settings.provider_name}


@app.get("/api/config")
def get_config():
    return {
        "provider": settings.provider_name,
        "max_upload_mb": settings.max_upload_mb,
        "allowed_extensions": list(settings.allowed_extensions),
    }


@app.post("/api/upload", status_code=202)
async def upload_audio(request: Request, audio_file: UploadFile = File(...)):
    filename = (audio_file.filename or "").strip()
    if not filename:
        raise HTTPException(status_code=400, detail="No file was provided.")
    ext = Path(filename).suffix.lower()
    if ext not in settings.allowed_extensions:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{ext or 'none'}'. "
                   f"Allowed: {', '.join(settings.allowed_extensions)}",
        )

    _check_rate_limit(request.client.host if request.client else "unknown")

    job_id = uuid.uuid4().hex
    file_path = store.uploads_dir / f"{job_id}{ext}"
    size = 0
    try:
        with open(file_path, "wb") as out:
            while chunk := await audio_file.read(1024 * 1024):
                size += len(chunk)
                if size > settings.max_upload_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File is too large. The maximum size is {settings.max_upload_mb} MB.",
                    )
                out.write(chunk)
    except HTTPException:
        file_path.unlink(missing_ok=True)
        raise
    if size == 0:
        file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")

    now = utc_now_iso()
    store.save({
        "id": job_id,
        "filename": Path(filename).name[:200],
        "status": "queued",
        "step": "Waiting in queue",
        "progress": 0,
        "error": None,
        "provider": settings.provider_name,
        "created_at": now,
        "updated_at": now,
    })
    if executor is None:
        raise HTTPException(status_code=503, detail="Server is starting up. Please retry.")
    executor.submit(process_lecture, job_id, file_path, store, settings)
    logger.info("Queued job %s (%s, %.1f MB)", job_id, filename, size / 1e6)
    return {"job_id": job_id, "status": "queued"}


@app.get("/api/status/{job_id}")
def get_status(job_id: str):
    job = _load_job(job_id)
    return {
        "status": job.get("status"),
        "step": job.get("step"),
        "progress": job.get("progress", 0),
        "error": job.get("error"),
    }


@app.get("/api/results/{job_id}")
def get_results(job_id: str):
    return _require_done(job_id)


@app.get("/api/export/{job_id}")
def export_notes(job_id: str, format: str = Query("pdf", pattern="^(pdf|md)$")):
    job = _require_done(job_id)
    if format == "md":
        from backend.services.markdown_export import generate_markdown
        return Response(
            content=generate_markdown(job),
            media_type="text/markdown; charset=utf-8",
            headers=_download_headers(job.get("filename"), "_notes.md"),
        )
    from backend.services.pdf_export import PDFExportService
    return Response(
        content=PDFExportService().generate(job),
        media_type="application/pdf",
        headers=_download_headers(job.get("filename"), "_notes.pdf"),
    )


@app.api_route("/api/{_path:path}", methods=["GET", "POST"], include_in_schema=False)
def api_not_found(_path: str):
    raise HTTPException(status_code=404, detail="Not found")


# ── Frontend (production build) ─────────────────────────────────────────────
_dist = settings.frontend_dist
if (_dist / "index.html").is_file():
    if (_dist / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=_dist / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        candidate = (_dist / full_path).resolve()
        if full_path and candidate.is_file() and _dist in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(_dist / "index.html", headers={"Cache-Control": "no-cache"})
else:
    @app.get("/", include_in_schema=False)
    def root():
        return {
            "message": "IntelliLecture API is running. Build the frontend "
                       "(cd frontend && npm run build) to serve the web app here.",
            "docs": "/api/docs",
        }
