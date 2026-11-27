"""
Summarizer Service (local mode) — facebook/bart-large-cnn.

Long transcripts are split on sentence boundaries into chunks that fit the
model's 1024-token window, summarised, then stitched into a structured result.
"""

import logging

from backend.services.text_utils import split_sentences

logger = logging.getLogger(__name__)

# ~1024 BART tokens ≈ 3,500 characters of English; leave headroom
MAX_CHUNK_CHARS = 3000


class SummarizerService:
    def __init__(self, model_name: str = "facebook/bart-large-cnn"):
        from transformers import pipeline  # deferred import: only needed in local mode
        logger.info("Loading summarization model: %s", model_name)
        self.summarizer = pipeline("summarization", model=model_name)
        logger.info("Summarization model loaded.")

    @staticmethod
    def _chunk_text(text: str) -> list[str]:
        chunks, current, size = [], [], 0
        for sentence in split_sentences(text):
            if current and size + len(sentence) > MAX_CHUNK_CHARS:
                chunks.append(" ".join(current))
                current, size = [], 0
            current.append(sentence)
            size += len(sentence) + 1
        if current:
            chunks.append(" ".join(current))
        return chunks

    def summarize(self, text: str) -> dict:
        if not text or len(text.strip()) < 50:
            return {
                "overview": "The transcript is too short to summarise.",
                "key_points": [],
                "important_concepts": [],
            }

        chunks = self._chunk_text(text)
        logger.info("Summarising %d chunks...", len(chunks))
        outputs = self.summarizer(
            chunks, max_length=150, min_length=30, do_sample=False, truncation=True,
        )
        chunk_summaries = [o["summary_text"].strip() for o in outputs]

        sentences: list[str] = []
        for s in split_sentences(" ".join(chunk_summaries)):
            if s not in sentences:
                sentences.append(s)

        # For long lectures, summarise the summaries to get a coherent overview
        if len(chunk_summaries) > 2:
            combined = " ".join(chunk_summaries)[: MAX_CHUNK_CHARS]
            overview = self.summarizer(
                combined, max_length=120, min_length=40, do_sample=False, truncation=True,
            )[0]["summary_text"].strip()
        else:
            overview = " ".join(sentences[:3])

        return {
            "overview": overview,
            "key_points": sentences,
            "important_concepts": [s for s in sentences if len(s.split()) <= 12],
        }
