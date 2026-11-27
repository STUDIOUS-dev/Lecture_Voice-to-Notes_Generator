"""
Quiz & Flashcard generation (local mode) using google/flan-t5-base.

Small models cannot reliably produce "5 MCQs" in one go, so the work is
broken into steps they handle well:
  - MCQs are built deterministically as fill-in-the-blank questions from
    key-point sentences, with other lecture keywords as distractors, so every
    question has real options and a known correct answer.
  - Short-answer questions and flashcards ask Flan-T5 to write ONE question
    per key point; the key point itself is the model answer.
"""

import logging
import random
import re

from backend.services.text_utils import split_sentences

logger = logging.getLogger(__name__)

DIFFICULTY_LABELS = ["Easy", "Medium", "Hard"]


def _difficulty(index: int) -> str:
    return DIFFICULTY_LABELS[index % len(DIFFICULTY_LABELS)]


def build_cloze_mcqs(sentences: list[str], keywords: list[str], count: int = 5,
                     seed: int = 42) -> list[dict]:
    """Create fill-in-the-blank MCQs using keywords as answers and distractors."""
    rng = random.Random(seed)
    mcqs: list[dict] = []
    used: set[str] = set()
    for sentence in sentences:
        if len(mcqs) >= count:
            break
        for kw in keywords:
            if kw.lower() in used:
                continue
            pattern = re.compile(rf"\b{re.escape(kw)}\b", re.IGNORECASE)
            if not pattern.search(sentence):
                continue
            distractors = [k for k in keywords if k.lower() != kw.lower()
                           and k.lower() not in kw.lower() and kw.lower() not in k.lower()]
            if len(distractors) < 3:
                continue
            options = rng.sample(distractors, 3) + [kw]
            rng.shuffle(options)
            mcqs.append({
                "question": "Fill in the blank: " + pattern.sub("_____", sentence, count=1),
                "options": options,
                "answer_index": options.index(kw),
                "explanation": sentence,
                "difficulty": _difficulty(len(mcqs)),
            })
            used.add(kw.lower())
            break
    return mcqs


class QuizService:
    def __init__(self, model_name: str = "google/flan-t5-base"):
        from transformers import pipeline  # deferred import: only needed in local mode
        logger.info("Loading quiz generation model: %s", model_name)
        self.generator = pipeline("text2text-generation", model=model_name)
        logger.info("Quiz model loaded.")

    def _question_for(self, sentence: str) -> str:
        prompt = f"Write one exam question that is answered by this statement: {sentence}"
        out = self.generator(prompt, max_length=64, num_beams=4, early_stopping=True)
        question = out[0]["generated_text"].strip()
        if not question.endswith("?"):
            question = question.rstrip(".") + "?"
        return question

    def _qa_pairs(self, statements: list[str], count: int) -> list[dict]:
        pairs, seen = [], set()
        for statement in statements:
            if len(pairs) >= count:
                break
            if len(statement.split()) < 5:
                continue
            question = self._question_for(statement)
            if question.lower() in seen or len(question) < 10:
                continue
            seen.add(question.lower())
            pairs.append({"question": question, "answer": statement})
        return pairs

    def generate_quiz(self, text: str, key_points: list[str] | None = None,
                      keywords: list[str] | None = None) -> dict:
        statements = key_points or split_sentences(text)[:20]
        mcqs = build_cloze_mcqs(statements + split_sentences(text), keywords or [])
        short_answers = [
            {**pair, "difficulty": _difficulty(i + 1)}
            for i, pair in enumerate(self._qa_pairs(statements, 3))
        ]
        logger.info("Generated %d MCQs and %d short answers.", len(mcqs), len(short_answers))
        return {"mcqs": mcqs, "short_answers": short_answers}

    def generate_flashcards(self, text: str, key_points: list[str] | None = None) -> list[dict]:
        statements = list(reversed(key_points or split_sentences(text)[:20]))
        cards = self._qa_pairs(statements, 6)
        logger.info("Generated %d flashcards.", len(cards))
        return cards
