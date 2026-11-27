"""
Local-model pipeline: Whisper + KeyBERT + BART + Flan-T5, all on this machine.

Models are loaded lazily on first use and cached for the process lifetime.
Requires the extra dependencies in `requirements-local.txt`.
"""

import logging
import threading
from pathlib import Path
from typing import Any, Callable

from backend.config import Settings

logger = logging.getLogger(__name__)

ProgressFn = Callable[[str, int], None]

_models: dict[str, Any] = {}
_model_lock = threading.Lock()


def _get(name: str, factory: Callable[[], Any]) -> Any:
    with _model_lock:
        if name not in _models:
            _models[name] = factory()
        return _models[name]


class LocalPipeline:
    def __init__(self, settings: Settings):
        self.settings = settings

    def transcribe(self, audio_path: Path, progress: ProgressFn) -> dict[str, Any]:
        from backend.services.asr import ASRService
        progress("Loading speech model", 8)
        asr = _get("asr", lambda: ASRService(self.settings.whisper_model_size))
        progress("Transcribing audio (this can take a while on CPU)", 12)
        return asr.transcribe(str(audio_path))

    def generate_materials(self, transcript: dict[str, Any], cleaned_text: str,
                           progress: ProgressFn) -> dict[str, Any]:
        from backend.services.nlp_utils import NLPUtils
        from backend.services.quiz_gen import QuizService
        from backend.services.summarizer import SummarizerService

        nlp = _get("nlp", NLPUtils)
        progress("Extracting keywords", 45)
        keywords = nlp.extract_keywords(cleaned_text, top_n=10)

        progress("Segmenting topics", 52)
        segments = nlp.segment_by_topic(cleaned_text)

        progress("Generating summary", 60)
        summary = _get("summarizer", SummarizerService).summarize(cleaned_text)

        progress("Generating quiz and flashcards", 78)
        quiz_svc = _get("quiz", QuizService)
        quiz = quiz_svc.generate_quiz(cleaned_text, summary["key_points"], keywords)
        flashcards = quiz_svc.generate_flashcards(cleaned_text, summary["key_points"])

        return {
            "summary": summary,
            "keywords": keywords,
            "segments": segments,
            "quiz": quiz,
            "flashcards": flashcards,
        }
