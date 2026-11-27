"""
Lecture processing pipeline: audio -> transcript -> study materials -> metrics.

The heavy lifting is delegated to either the hosted-API pipeline or the
local-model pipeline, depending on configuration. Both return the same
result shape, so the API and frontend don't care which one ran.
"""

import logging
from pathlib import Path

from backend.config import Settings
from backend.jobs import JobStore
from backend.services import audio
from backend.services.evaluator import EvaluatorService
from backend.services.llm_client import APIError
from backend.services.text_utils import clean_text

logger = logging.getLogger(__name__)


def get_pipeline(settings: Settings):
    if settings.use_api:
        from backend.services.cloud import CloudPipeline
        return CloudPipeline(settings)
    from backend.services.local import LocalPipeline
    return LocalPipeline(settings)


def process_lecture(job_id: str, audio_path: Path, store: JobStore, settings: Settings) -> None:
    def progress(step: str, percent: int) -> None:
        store.update(job_id, status="processing", step=step, progress=max(0, min(99, percent)))
        logger.info("[%s] %s (%d%%)", job_id, step, percent)

    try:
        progress("Preparing audio", 3)
        duration = audio.get_duration(audio_path)
        store.update(job_id, duration_seconds=duration)

        pipeline = get_pipeline(settings)

        transcript = pipeline.transcribe(audio_path, progress)
        raw_text = transcript.get("text", "")
        if len(raw_text.split()) < 5:
            raise ValueError("No speech was detected in the audio file.")
        cleaned = clean_text(raw_text)
        store.update(job_id, transcript=transcript, cleaned_text=cleaned)

        materials = pipeline.generate_materials(transcript, cleaned, progress)

        progress("Calculating metrics", 95)
        summary = materials["summary"]
        summary_text = " ".join([summary.get("overview", "")] + summary.get("key_points", []))
        metrics = EvaluatorService().calculate_metrics(transcript=cleaned, summary=summary_text)

        store.update(
            job_id,
            **materials,
            metrics=metrics,
            status="done",
            step="Complete",
            progress=100,
            error=None,
        )
        logger.info("[%s] Processing complete", job_id)

    except (APIError, audio.AudioError, ValueError) as exc:
        # Expected failures: show the message to the user
        logger.warning("[%s] Processing failed: %s", job_id, exc)
        store.update(job_id, status="error", step="Failed", error=str(exc))
    except Exception:  # noqa: BLE001 - never leak internals to the client
        logger.exception("[%s] Unexpected pipeline error", job_id)
        store.update(
            job_id, status="error", step="Failed",
            error="An unexpected error occurred while processing the lecture. Please try again.",
        )
    finally:
        # Audio is no longer needed once processed; don't keep user recordings around
        try:
            audio_path.unlink(missing_ok=True)
        except OSError:
            logger.warning("[%s] Could not delete upload %s", job_id, audio_path)
