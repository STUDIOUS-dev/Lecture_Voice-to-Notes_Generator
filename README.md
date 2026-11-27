# IntelliLecture — AI Lecture Voice-to-Notes Generator

Upload a lecture recording and get, in about a minute:

- **Transcript** with timestamps and search
- **Summary**: overview, key points and important concepts
- **Topic breakdown** with jump-in timestamps and keywords
- **Interactive quiz**: multiple-choice questions with answers & explanations, plus short-answer questions with model answers
- **Flashcards** you can flip through
- **Export** to PDF or Markdown (Notion / Obsidian friendly)

Built with a **FastAPI** backend and a **React + Vite** frontend, deployable as a single Docker container.

---

## How it works

```
Audio upload ─► Speech-to-text ─► Clean-up ─► Study-material generation ─► Metrics ─► Dashboard / PDF / Markdown
                 (Whisper)                     (LLM or local models)       (ROUGE)
```

The AI backend is **switchable** via the `AI_PROVIDER` setting:

| Mode | Speech-to-text | Notes, quiz & flashcards | Speed (1-hr lecture) | Needs |
|---|---|---|---|---|
| **API** (recommended) | `whisper-large-v3-turbo` | `llama-3.3-70b-versatile` | ~1–3 min | Free [Groq API key](https://console.groq.com/keys) |
| **Local** | Whisper `base` | BART-large-CNN, KeyBERT, Flan-T5 | 10–25 min on CPU | ~4 GB RAM, `requirements-local.txt` |

`AI_PROVIDER=auto` (default) uses the API when a key is set and falls back to local models otherwise.
Any OpenAI-compatible API works (OpenAI, Together, a local Ollama, …) via `LLM_BASE_URL`, `LLM_API_KEY` and `LLM_MODEL`.

Long lectures are handled map-reduce style: the transcript is split into timestamped chunks, each chunk is turned into topic sections, and a final pass produces the summary, quiz and flashcards. This keeps every request within free-tier limits, and rate-limit responses are retried automatically.

---

## Quick start (local development)

**Prerequisites:** Python 3.10+, Node.js 18+, and [FFmpeg](https://ffmpeg.org/download.html)
(`brew install ffmpeg` / `sudo apt install ffmpeg` / on Windows, put `ffmpeg.exe` in the project root).

```bash
# 1. Python environment
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
# Optional, for offline local models:
# pip install -r requirements-local.txt

# 2. Configuration
cp .env.example .env              # then paste your GROQ_API_KEY into .env

# 3. Run backend + frontend together (with the venv activated)
cd frontend
npm install
npm run dev
```

- App: <http://localhost:5173>
- API docs: <http://localhost:8000/api/docs>

---

## Deploying as a live website

The `Dockerfile` builds the frontend and serves it from the API, so the whole site is **one service on one URL**.

### Option A — Render (free, easiest)

1. Get a free API key at <https://console.groq.com/keys>.
2. Push this repository to GitHub.
3. On [Render](https://dashboard.render.com): **New → Blueprint** → pick this repository. `render.yaml` sets everything up.
4. Paste your `GROQ_API_KEY` when prompted, then deploy. Your site is live at `https://intellilecture-xxxx.onrender.com`.

> Free Render instances sleep after 15 minutes of inactivity (the first request after that takes ~30 s) and have no persistent disk. That's fine here because results are temporary anyway.

### Option B — Hugging Face Spaces (free, 16 GB RAM — can also run local models)

1. Create a new Space at <https://huggingface.co/new-space> and choose **Docker → Blank**.
2. Push this repository to the Space, replacing the Space's `README.md` with [`deploy/huggingface/README.md`](deploy/huggingface/README.md) (it contains the required config header).
3. In **Settings → Variables and secrets**, add the secret `GROQ_API_KEY`.
   - Prefer no API key? Add the variable `AI_PROVIDER=local` and set the build argument `INSTALL_LOCAL_MODELS=true` in the Dockerfile. Processing will be much slower.

### Option C — Any Docker host (Railway, Fly.io, Google Cloud Run, a VPS)

```bash
docker build -t intellilecture .
docker run -p 8000:8000 -e GROQ_API_KEY=your_key intellilecture
```

The container listens on `$PORT` (default `8000`), so it works on platforms that inject a port.
Build with `--build-arg INSTALL_LOCAL_MODELS=true` to include the offline model stack.

### Option D — Separate frontend (Vercel / Netlify) + API

Build the frontend with `VITE_API_URL=https://your-api.example.com`, deploy `frontend/dist`, and set
`ALLOWED_ORIGINS=https://your-frontend.example.com` on the API.

### Before going public

- Keep your API key in the host's secret settings, never in the repository.
- Tune `UPLOADS_PER_HOUR` (per-IP limit), `MAX_UPLOAD_MB` and `MAX_CONCURRENT_JOBS` to protect your API quota.
- Uploaded audio is deleted right after processing, and results expire after `JOB_TTL_HOURS` (default 48).

---

## Configuration

All settings are environment variables (or a `.env` file). See [`.env.example`](.env.example).

| Variable | Default | Description |
|---|---|---|
| `AI_PROVIDER` | `auto` | `auto`, `api` or `local` |
| `GROQ_API_KEY` / `LLM_API_KEY` | – | API key for the hosted provider |
| `LLM_BASE_URL` | Groq | Any OpenAI-compatible base URL |
| `LLM_MODEL` | `llama-3.3-70b-versatile` | Chat model for notes, quiz and flashcards |
| `TRANSCRIPTION_MODEL` | `whisper-large-v3-turbo` | Hosted speech-to-text model |
| `WHISPER_MODEL` | `base` | Local Whisper size |
| `MAX_UPLOAD_MB` | `100` | Upload size limit |
| `UPLOADS_PER_HOUR` | `10` | Per-IP upload limit (`0` disables it) |
| `MAX_CONCURRENT_JOBS` | `2` | Lectures processed in parallel |
| `JOB_TTL_HOURS` | `48` | How long results are kept |
| `ALLOWED_ORIGINS` | localhost | CORS origins (only needed for a separately hosted frontend) |

---

## API

Interactive docs are served at `/api/docs`.

| Endpoint | Method | Description |
|---|---|---|
| `/api/health` | GET | Health check |
| `/api/config` | GET | Upload limits and active AI provider |
| `/api/upload` | POST | Upload audio (`multipart/form-data`, field `audio_file`) → `job_id` |
| `/api/status/{job_id}` | GET | Status, current step and progress (0–100) |
| `/api/results/{job_id}` | GET | Full results |
| `/api/export/{job_id}?format=pdf\|md` | GET | Download notes as PDF or Markdown |

---

## Project structure

```
├── backend/
│   ├── main.py               # FastAPI app: API routes, rate limiting, serves frontend build
│   ├── config.py             # Environment-based settings
│   ├── jobs.py               # Thread-safe, atomic JSON job store with auto-cleanup
│   ├── pipeline.py           # Orchestrates transcription → notes → metrics
│   └── services/
│       ├── cloud.py          # Hosted API pipeline (Whisper + LLM, map-reduce)
│       ├── llm_client.py     # OpenAI-compatible client with rate-limit-aware retries
│       ├── local.py          # Local model pipeline
│       ├── asr.py            # Local Whisper
│       ├── summarizer.py     # Local BART summarisation
│       ├── nlp_utils.py      # Local KeyBERT keywords + topic segmentation
│       ├── quiz_gen.py       # Local quiz & flashcards (Flan-T5 + cloze MCQs)
│       ├── audio.py          # FFmpeg helpers (duration, compression, splitting)
│       ├── text_utils.py     # Text cleaning + output validation
│       ├── evaluator.py      # ROUGE / WER / compression metrics
│       ├── pdf_export.py     # PDF export (ReportLab)
│       └── markdown_export.py
├── frontend/                 # React + Vite app
├── tests/                    # Backend test suite (pytest)
├── deploy/huggingface/       # Hugging Face Spaces config
├── Dockerfile                # Production image (frontend + API)
├── render.yaml               # Render blueprint
├── requirements.txt          # Core dependencies (API mode)
├── requirements-local.txt    # Optional local model dependencies
└── requirements-dev.txt      # Test dependencies
```

## Running tests

```bash
pip install -r requirements-dev.txt
pytest
```

The tests use a fake AI pipeline, so they run in seconds without an API key or model downloads.
