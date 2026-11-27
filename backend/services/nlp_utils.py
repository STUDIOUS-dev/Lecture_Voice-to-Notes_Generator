"""
NLP Utilities (local mode) — keyword extraction and topic segmentation.

Uses:
  - KeyBERT for keyword extraction
  - SentenceTransformers + cosine similarity for topic segmentation

Both share a single all-MiniLM-L6-v2 model to save memory.
"""

import logging

from backend.services.text_utils import clean_text, split_sentences

logger = logging.getLogger(__name__)

# Similarity between neighbouring windows below which a new topic starts
TOPIC_SIMILARITY_THRESHOLD = 0.35
# Sentences per sliding window (smooths out noise from single short sentences)
WINDOW = 3
# Segments shorter than this many sentences are merged into the previous one
MIN_SEGMENT_SENTENCES = 4


class NLPUtils:
    def __init__(self):
        from keybert import KeyBERT  # deferred imports: only needed in local mode
        from sentence_transformers import SentenceTransformer
        logger.info("Loading SentenceTransformer + KeyBERT...")
        self.embedder = SentenceTransformer("all-MiniLM-L6-v2")
        self.kw_model = KeyBERT(model=self.embedder)
        logger.info("NLP models loaded.")

    # Kept for backwards compatibility with older callers
    clean_text = staticmethod(clean_text)

    def extract_keywords(self, text: str, top_n: int = 10) -> list[str]:
        if not text or len(text.strip()) < 20:
            return []
        keywords = self.kw_model.extract_keywords(
            text,
            keyphrase_ngram_range=(1, 2),
            stop_words="english",
            top_n=top_n,
            use_mmr=True,  # Maximal Marginal Relevance: diverse, non-redundant phrases
            diversity=0.5,
        )
        return [kw for kw, _score in keywords]

    def segment_by_topic(self, text: str) -> list[dict]:
        """
        Split the transcript into topically coherent sections by comparing
        embeddings of neighbouring sentence windows. All sentences are
        encoded in a single batch (previously each sentence was encoded twice,
        one call at a time).
        """
        sentences = split_sentences(text)
        if len(sentences) <= MIN_SEGMENT_SENTENCES:
            return [{"title": "Topic 1", "content": text, "start": None}] if text else []

        from sentence_transformers import util as st_util

        embeddings = self.embedder.encode(sentences, convert_to_tensor=True, batch_size=64)
        boundaries = [0]
        for i in range(WINDOW, len(sentences) - WINDOW + 1):
            before = embeddings[i - WINDOW:i].mean(dim=0)
            after = embeddings[i:i + WINDOW].mean(dim=0)
            if (float(st_util.cos_sim(before, after)) < TOPIC_SIMILARITY_THRESHOLD
                    and i - boundaries[-1] >= MIN_SEGMENT_SENTENCES):
                boundaries.append(i)
        boundaries.append(len(sentences))

        segments = []
        for n, (start, end) in enumerate(zip(boundaries, boundaries[1:]), 1):
            content = " ".join(sentences[start:end])
            title_kw = self.extract_keywords(content, top_n=1)
            title = title_kw[0].title() if title_kw else f"Topic {n}"
            segments.append({"title": title, "content": content, "start": None})

        logger.info("Found %d topic segments.", len(segments))
        return segments
