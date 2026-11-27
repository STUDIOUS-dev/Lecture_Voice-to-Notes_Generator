"""
Evaluator Service — summary quality metrics.

  - ROUGE-1 / ROUGE-L F1 between transcript and summary (rouge-score)
  - Compression ratio (summary words / transcript words)
  - Word Error Rate against an optional ground-truth transcript (jiwer)
"""

import logging

from backend.services.text_utils import word_count

logger = logging.getLogger(__name__)


class EvaluatorService:
    def calculate_wer(self, reference: str, hypothesis: str) -> float | None:
        """Word Error Rate (lower is better). Needs a ground-truth reference."""
        if not reference or not hypothesis:
            return None
        try:
            from jiwer import wer
        except ImportError:
            logger.warning("jiwer not installed; skipping WER")
            return None
        return round(wer(reference.lower().strip(), hypothesis.lower().strip()), 4)

    def calculate_rouge(self, reference: str, hypothesis: str) -> dict:
        """ROUGE-1 and ROUGE-L F1 scores (higher means more content overlap)."""
        if not reference or not hypothesis:
            return {"rouge1": None, "rougeL": None}
        try:
            from rouge_score import rouge_scorer
        except ImportError:
            logger.warning("rouge-score not installed; skipping ROUGE")
            return {"rouge1": None, "rougeL": None}
        scorer = rouge_scorer.RougeScorer(["rouge1", "rougeL"], use_stemmer=True)
        scores = scorer.score(reference, hypothesis)
        return {
            "rouge1": round(scores["rouge1"].fmeasure, 4),
            "rougeL": round(scores["rougeL"].fmeasure, 4),
        }

    def calculate_metrics(self, transcript: str, summary: str,
                          reference_transcript: str | None = None) -> dict:
        transcript_words = word_count(transcript)
        metrics = {
            "wer": self.calculate_wer(reference_transcript, transcript) if reference_transcript else None,
            "word_count": transcript_words,
            "compression_ratio": (
                round(word_count(summary) / transcript_words, 4) if transcript_words else None
            ),
        }
        metrics.update(self.calculate_rouge(transcript, summary))
        logger.info("Evaluation metrics: %s", metrics)
        return metrics
