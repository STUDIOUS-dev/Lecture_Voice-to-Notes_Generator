"""
Hosted-API pipeline: Whisper transcription + LLM-generated study notes.

Works with any OpenAI-compatible provider (Groq by default). Long lectures
are processed map-reduce style: each chunk of the transcript is summarised
into a timestamped section, then a final request turns the section notes
into the overview, quiz and flashcards. Every request stays small enough
for free-tier token-per-minute limits.
"""

import logging
import tempfile
from pathlib import Path
from typing import Any, Callable

from backend.config import Settings
from backend.services import audio
from backend.services.llm_client import LLMClient
from backend.services.text_utils import (
    normalize_mcqs, normalize_qa, normalize_sections, normalize_summary, _str_list,
)

logger = logging.getLogger(__name__)

ProgressFn = Callable[[str, int], None]

# Hosted Whisper endpoints typically accept up to 25 MB per request
MAX_API_AUDIO_BYTES = 24 * 1024 * 1024
SPLIT_SECONDS = 20 * 60

SYSTEM_PROMPT = (
    "You are an expert teaching assistant who turns lecture transcripts into accurate, "
    "well-organised study material for students. Use only information from the lecture; "
    "never invent facts. Write clearly and concisely. Always reply with a single valid "
    "JSON object that follows the requested schema exactly."
)

SECTION_PROMPT = """Below is part {part} of {total} of a lecture transcript. Each line starts with its start time in seconds in square brackets.

Split this part into 1-4 coherent topic sections. Return JSON:
{{
  "sections": [
    {{"title": "short descriptive title (max 8 words)",
      "start_seconds": <number taken from the line where the section begins>,
      "summary": "3-6 sentence summary of what is taught in this section, keeping definitions, formulas, examples and numbers"}}
  ]
}}

Transcript:
{transcript}"""

MATERIALS_PROMPT = """Create study material for the lecture below. {source_note}

Return JSON with exactly these keys:
{{
  "overview": "one paragraph (3-5 sentences) explaining what the lecture covers and its main takeaway",
  "key_points": ["8-12 standalone sentences, each one important idea from the lecture"],
  "important_concepts": ["6-10 entries formatted as 'Term: one-sentence definition'"],
  "keywords": ["10 short keyphrases (1-3 words)"],{sections_schema}
  "mcqs": [
    {{"question": "...", "options": ["...", "...", "...", "..."], "answer_index": <0-3>,
      "explanation": "one sentence on why the answer is correct",
      "difficulty": "Easy|Medium|Hard"}}
  ],
  "short_answers": [{{"question": "...", "answer": "2-3 sentence model answer", "difficulty": "Easy|Medium|Hard"}}],
  "flashcards": [{{"question": "front of card", "answer": "back of card (concise)"}}]
}}

Rules: write exactly 5 mcqs (mixed difficulty, one clearly correct option each, plausible distractors, vary the position of the correct option), 3 short_answers and 8 flashcards. Every question must be answerable from the lecture.

{label}:
{content}"""

SECTIONS_SCHEMA = """
  "sections": [{"title": "short title", "start_seconds": <number from the line where it begins>, "summary": "3-5 sentence summary"}],"""


def _fmt_lines(segments: list[dict[str, Any]]) -> str:
    return "\n".join(f"[{int(s['start'])}] {s['text']}" for s in segments if s.get("text"))


def _chunk_segments(segments: list[dict[str, Any]], max_chars: int) -> list[list[dict[str, Any]]]:
    chunks: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    size = 0
    for seg in segments:
        length = len(seg.get("text", "")) + 8
        if current and size + length > max_chars:
            chunks.append(current)
            current, size = [], 0
        current.append(seg)
        size += length
    if current:
        chunks.append(current)
    return chunks


class CloudPipeline:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = LLMClient(settings.api_base_url, settings.api_key)

    # ── Transcription ───────────────────────────────────────────────────────
    def transcribe(self, audio_path: Path, progress: ProgressFn) -> dict[str, Any]:
        with tempfile.TemporaryDirectory(prefix="intellilecture_") as tmp:
            tmp_dir = Path(tmp)
            source = audio_path
            if audio.ffmpeg_available():
                progress("Optimising audio", 8)
                source = audio.compress_for_speech(audio_path, tmp_dir / "speech.mp3")

            if source.stat().st_size > MAX_API_AUDIO_BYTES:
                if not audio.ffmpeg_available():
                    raise audio.AudioError(
                        "File is too large for the transcription API and ffmpeg is unavailable."
                    )
                parts = audio.split_audio(source, tmp_dir / "parts", SPLIT_SECONDS)
            else:
                parts = [source]

            text_parts: list[str] = []
            segments: list[dict[str, Any]] = []
            language = None
            for i, part in enumerate(parts):
                offset = float(i * SPLIT_SECONDS)  # parts are cut at fixed intervals
                progress(
                    f"Transcribing audio{f' (part {i + 1} of {len(parts)})' if len(parts) > 1 else ''}",
                    10 + int(30 * i / len(parts)),
                )
                result = self.client.transcribe(self.settings.transcription_model, part)
                language = language or result.get("language")
                text_parts.append((result.get("text") or "").strip())
                for seg in result.get("segments") or []:
                    segments.append({
                        "start": round(float(seg.get("start", 0)) + offset, 2),
                        "end": round(float(seg.get("end", 0)) + offset, 2),
                        "text": (seg.get("text") or "").strip(),
                    })

        return {
            "text": " ".join(t for t in text_parts if t).strip(),
            "segments": segments,
            "language": language,
        }

    # ── Study material generation ────────────────────────────────────────────
    def _chat(self, prompt: str, max_tokens: int = 4096) -> dict[str, Any]:
        return self.client.chat_json(self.settings.llm_model, SYSTEM_PROMPT, prompt,
                                     max_tokens=max_tokens)

    def generate_materials(self, transcript: dict[str, Any], cleaned_text: str,
                           progress: ProgressFn) -> dict[str, Any]:
        segments = transcript.get("segments") or []
        if not segments:
            segments = [{"start": 0, "end": 0, "text": cleaned_text}]
        chunks = _chunk_segments(segments, self.settings.llm_chunk_chars)

        if len(chunks) == 1:
            progress("Generating notes, quiz and flashcards", 60)
            data = self._chat(MATERIALS_PROMPT.format(
                source_note="",
                sections_schema=SECTIONS_SCHEMA,
                label="Transcript (each line starts with its start time in seconds)",
                content=_fmt_lines(chunks[0]),
            ))
            sections = normalize_sections(data.get("sections"))
        else:
            sections = []
            for i, chunk in enumerate(chunks):
                progress(f"Analysing lecture (part {i + 1} of {len(chunks)})",
                         45 + int(35 * i / len(chunks)))
                part = self._chat(SECTION_PROMPT.format(
                    part=i + 1, total=len(chunks), transcript=_fmt_lines(chunk),
                ), max_tokens=2048)
                found = normalize_sections(part.get("sections"))
                if not found:  # fall back to one untitled section for the chunk
                    found = [{"title": f"Part {i + 1}", "start": chunk[0].get("start"),
                              "content": " ".join(s["text"] for s in chunk)[:1500]}]
                sections.extend(found)

            progress("Generating notes, quiz and flashcards", 82)
            notes = "\n\n".join(
                f"## {s['title']}\n{s['content']}" for s in sections
            )
            data = self._chat(MATERIALS_PROMPT.format(
                source_note="The lecture was long, so you are given detailed section-by-section notes of it.",
                sections_schema="",
                label="Lecture notes",
                content=notes,
            ))

        return {
            "summary": normalize_summary(data),
            "keywords": _str_list(data.get("keywords"), limit=12),
            "segments": sections,
            "quiz": {
                "mcqs": normalize_mcqs(data.get("mcqs")),
                "short_answers": normalize_qa(data.get("short_answers"), with_difficulty=True),
            },
            "flashcards": normalize_qa(data.get("flashcards")),
        }
