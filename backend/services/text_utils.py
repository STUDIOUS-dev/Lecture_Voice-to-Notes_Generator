"""
Lightweight text helpers shared by both pipelines (no ML dependencies).
"""

import hashlib
import random
import re
from typing import Any

# Only true disfluencies. Words such as "like", "so", "right" or "actually"
# carry meaning in lectures ("a list is like an array"), so they are kept.
_FILLER_RE = re.compile(r"\b(?:u+h+m*|u+m+|e+r+m+|h+m+|a+h+)\b[,.]?\s*", re.IGNORECASE)
# Immediately repeated words: "the the" -> "the"
_REPEAT_RE = re.compile(r"\b(\w+)(\s+\1\b)+", re.IGNORECASE)
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])")


def clean_text(text: str) -> str:
    """Remove filler sounds and stutters, normalise whitespace."""
    if not text:
        return ""
    cleaned = _FILLER_RE.sub("", text)
    cleaned = _REPEAT_RE.sub(r"\1", cleaned)
    cleaned = re.sub(r"\s+([,.!?;:])", r"\1", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    return cleaned.strip()


def split_sentences(text: str) -> list[str]:
    """Split text into sentences without breaking on decimals like 3.14."""
    if not text:
        return []
    return [s.strip() for s in _SENTENCE_RE.split(text.strip()) if s.strip()]


def word_count(text: str) -> int:
    return len(text.split()) if text else 0


# ── Schema normalisation ────────────────────────────────────────────────────
# Model output is never fully trusted: these coerce whatever came back into
# the exact shape the frontend and PDF exporter expect.

def _str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        for key in ("text", "term", "question", "title", "value"):
            if key in value:
                return _str(value[key])
    return str(value).strip()


def _str_list(value: Any, limit: int | None = None) -> list[str]:
    if not isinstance(value, list):
        return []
    items: list[str] = []
    for item in value:
        if isinstance(item, dict) and "term" in item and "definition" in item:
            text = f"{_str(item['term'])}: {_str(item['definition'])}"
        else:
            text = _str(item)
        if text and text not in items:
            items.append(text)
    return items[:limit] if limit else items


def _difficulty(value: Any, index: int) -> str:
    text = _str(value).capitalize()
    return text if text in ("Easy", "Medium", "Hard") else ("Easy", "Medium", "Hard")[index % 3]


def _float_or_none(value: Any) -> float | None:
    try:
        return round(float(value), 2) if value is not None else None
    except (TypeError, ValueError):
        return None


def normalize_summary(data: Any) -> dict[str, Any]:
    data = data if isinstance(data, dict) else {}
    return {
        "overview": _str(data.get("overview")),
        "key_points": _str_list(data.get("key_points")),
        "important_concepts": _str_list(data.get("important_concepts")),
    }


def normalize_sections(data: Any) -> list[dict[str, Any]]:
    sections = []
    for i, item in enumerate(data if isinstance(data, list) else []):
        if not isinstance(item, dict):
            continue
        content = _str(item.get("content") or item.get("summary"))
        if not content:
            continue
        sections.append({
            "title": _str(item.get("title")) or f"Topic {i + 1}",
            "content": content,
            "start": _float_or_none(item.get("start", item.get("start_seconds"))),
        })
    return sections


def normalize_mcqs(data: Any) -> list[dict[str, Any]]:
    mcqs = []
    for i, item in enumerate(data if isinstance(data, list) else []):
        if not isinstance(item, dict):
            continue
        question = _str(item.get("question"))
        if not question:
            continue
        options = _str_list(item.get("options"))
        answer_index = item.get("answer_index")
        if not isinstance(answer_index, int) or not 0 <= answer_index < len(options):
            # Accept a letter ("B") or the answer text as fallbacks
            answer = _str(item.get("answer"))
            answer_index = None
            if len(answer) == 1 and answer.upper() in "ABCDEF":
                idx = "ABCDEF".index(answer.upper())
                answer_index = idx if idx < len(options) else None
            elif answer in options:
                answer_index = options.index(answer)
        if answer_index is not None and len(options) > 1:
            # LLMs tend to put the right answer in the same slot every time;
            # move it to a position derived from the question (stable across reloads).
            seed = int(hashlib.sha256(question.encode()).hexdigest()[:8], 16)
            target = random.Random(seed).randrange(len(options))
            options[answer_index], options[target] = options[target], options[answer_index]
            answer_index = target
        mcqs.append({
            "question": question,
            "options": options,
            "answer_index": answer_index,
            "explanation": _str(item.get("explanation")),
            "difficulty": _difficulty(item.get("difficulty"), i),
        })
    return mcqs


def normalize_qa(data: Any, with_difficulty: bool = False) -> list[dict[str, Any]]:
    pairs = []
    for i, item in enumerate(data if isinstance(data, list) else []):
        if not isinstance(item, dict):
            continue
        question = _str(item.get("question") or item.get("front"))
        answer = _str(item.get("answer") or item.get("back"))
        if not question:
            continue
        pair: dict[str, Any] = {"question": question, "answer": answer}
        if with_difficulty:
            pair["difficulty"] = _difficulty(item.get("difficulty"), i)
        pairs.append(pair)
    return pairs
