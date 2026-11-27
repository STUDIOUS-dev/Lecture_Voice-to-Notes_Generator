import time

import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

import pytest
from fastapi.testclient import TestClient

import backend.pipeline as pipeline_mod
from backend.main import app

FAKE_TRANSCRIPT = {
    "text": "Um, today we learn about sorting & searching <algorithms>. Binary search halves the range.",
    "segments": [{"start": 0.0, "end": 4.2, "text": "Today we learn about sorting."}],
}


class FakePipeline:
    def __init__(self, settings):
        pass

    def transcribe(self, audio_path, progress):
        progress("Transcribing audio", 10)
        return FAKE_TRANSCRIPT

    def generate_materials(self, transcript, cleaned_text, progress):
        progress("Generating notes", 60)
        return {
            "summary": {"overview": "Sorting & searching.", "key_points": ["Binary search halves the range."],
                        "important_concepts": ["Binary search: halving <search>"]},
            "keywords": ["binary search", "sorting"],
            "segments": [{"title": "Intro", "content": "Sorting basics", "start": 0}],
            "quiz": {"mcqs": [{"question": "What halves the range?", "options": ["Binary search", "Bubble sort",
                               "Hashing", "DFS"], "answer_index": 0, "explanation": "By definition.",
                               "difficulty": "Easy"}],
                     "short_answers": [{"question": "Explain binary search.", "answer": "It halves.",
                                        "difficulty": "Medium"}]},
            "flashcards": [{"question": "Binary search complexity?", "answer": "O(log n)"}],
        }


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setattr(pipeline_mod, "get_pipeline", lambda settings: FakePipeline(settings))
    with TestClient(app) as c:
        yield c


def _wait_done(client, job_id, timeout=10):
    deadline = time.time() + timeout
    while time.time() < deadline:
        status = client.get(f"/api/status/{job_id}").json()
        if status["status"] in ("done", "error"):
            return status
        time.sleep(0.05)
    raise AssertionError("job did not finish")


def test_health_and_config(client):
    assert client.get("/api/health").json()["status"] == "ok"
    cfg = client.get("/api/config").json()
    assert cfg["max_upload_mb"] == 1
    assert ".mp3" in cfg["allowed_extensions"]


def test_full_flow_and_exports(client):
    res = client.post("/api/upload", files={"audio_file": ("My Lecture é.mp3", b"ID3fakeaudio", "audio/mpeg")})
    assert res.status_code == 202, res.text
    job_id = res.json()["job_id"]

    status = _wait_done(client, job_id)
    assert status["status"] == "done", status
    assert status["progress"] == 100

    results = client.get(f"/api/results/{job_id}").json()
    assert results["filename"] == "My Lecture é.mp3"
    assert results["cleaned_text"].startswith("today we learn")
    assert results["metrics"]["word_count"] > 0
    assert results["metrics"]["rouge1"] is not None
    assert results["quiz"]["mcqs"][0]["options"][0] == "Binary search"

    pdf = client.get(f"/api/export/{job_id}?format=pdf")
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    assert "attachment" in pdf.headers["content-disposition"]

    md = client.get(f"/api/export/{job_id}?format=md")
    assert md.status_code == 200
    assert "## Quiz" in md.text and "**Answer:** A. Binary search" in md.text

    assert client.get(f"/api/export/{job_id}?format=exe").status_code == 422


def test_upload_validation(client):
    assert client.post("/api/upload", files={"audio_file": ("x.exe", b"abc", "application/octet-stream")}).status_code == 415
    assert client.post("/api/upload", files={"audio_file": ("x.mp3", b"", "audio/mpeg")}).status_code == 400
    big = b"0" * (1024 * 1024 + 10)
    assert client.post("/api/upload", files={"audio_file": ("x.mp3", big, "audio/mpeg")}).status_code == 413


def test_invalid_and_unknown_job_ids(client):
    assert client.get("/api/status/..%2F..%2Fetc").status_code == 404
    assert client.get("/api/status/" + "0" * 32).status_code == 404
    assert client.get("/api/unknown").status_code == 404


def test_pipeline_errors_are_sanitised(client, monkeypatch):
    class Boom(FakePipeline):
        def transcribe(self, audio_path, progress):
            raise RuntimeError("secret internal path /root/x")

    monkeypatch.setattr(pipeline_mod, "get_pipeline", lambda settings: Boom(settings))
    job_id = client.post("/api/upload", files={"audio_file": ("a.wav", b"RIFF", "audio/wav")}).json()["job_id"]
    status = _wait_done(client, job_id)
    assert status["status"] == "error"
    assert "secret" not in status["error"]
    assert client.get(f"/api/results/{job_id}").status_code == 409


def test_rate_limit(client, monkeypatch):
    from backend import main
    import dataclasses
    monkeypatch.setattr(main, "settings", dataclasses.replace(main.settings, uploads_per_hour=1))
    main._upload_log.clear()
    ok = client.post("/api/upload", files={"audio_file": ("a.mp3", b"x", "audio/mpeg")})
    assert ok.status_code == 202
    limited = client.post("/api/upload", files={"audio_file": ("a.mp3", b"x", "audio/mpeg")})
    assert limited.status_code == 429
    main._upload_log.clear()
