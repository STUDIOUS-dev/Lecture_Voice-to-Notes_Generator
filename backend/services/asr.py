"""
ASR Service — local Speech-to-Text using OpenAI Whisper.

Loads the Whisper model once and exposes `transcribe()`, which returns the
full text plus per-segment timestamps.
"""

import logging

import backend.services.audio  # noqa: F401  (adds a bundled ffmpeg.exe to PATH on Windows)

logger = logging.getLogger(__name__)


class ASRService:
    """
    Automatic Speech Recognition using OpenAI Whisper.

    Supported model sizes: tiny, base, small, medium, large.
    Larger models are more accurate but slower; 'base' is a good CPU default.
    """

    def __init__(self, model_size: str = "base"):
        import whisper  # deferred import: only needed in local mode
        logger.info("Loading Whisper model: %s", model_size)
        self.model = whisper.load_model(model_size)
        logger.info("Whisper model loaded.")

    def transcribe(self, audio_path: str) -> dict:
        logger.info("Transcribing audio: %s", audio_path)
        # fp16 is unsupported on CPU; disabling it avoids a noisy warning
        result = self.model.transcribe(str(audio_path), verbose=None, fp16=False)
        segments = [
            {
                "start": round(seg["start"], 2),
                "end": round(seg["end"], 2),
                "text": seg["text"].strip(),
            }
            for seg in result.get("segments", [])
        ]
        logger.info("Transcription complete: %d segments.", len(segments))
        return {
            "text": result["text"].strip(),
            "segments": segments,
            "language": result.get("language"),
        }
