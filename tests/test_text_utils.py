from backend.services.quiz_gen import build_cloze_mcqs
from backend.services.text_utils import (
    clean_text, normalize_mcqs, normalize_qa, normalize_sections, normalize_summary, split_sentences,
)


def test_clean_text_removes_fillers_but_keeps_meaningful_words():
    text = "Um, so a list is like an array. Uh the the index starts at zero, right?"
    cleaned = clean_text(text)
    assert "Um" not in cleaned and "Uh" not in cleaned
    assert "like an array" in cleaned
    assert "so a list" in cleaned
    assert "right?" in cleaned
    assert "the the" not in cleaned


def test_split_sentences_keeps_decimals():
    assert split_sentences("Pi is 3.14 roughly. Next topic! Done?") == [
        "Pi is 3.14 roughly.", "Next topic!", "Done?",
    ]


def test_normalize_mcqs_handles_letters_and_bad_data():
    mcqs = normalize_mcqs([
        {"question": "Q1", "options": ["a", "b", "c", "d"], "answer": "C"},
        {"question": "Q2", "options": ["x", "y"], "answer_index": 7, "difficulty": "hard"},
        {"question": "", "options": []},
        "garbage",
    ])
    assert len(mcqs) == 2
    assert mcqs[0]["answer_index"] == 2
    assert mcqs[1]["answer_index"] is None
    assert mcqs[1]["difficulty"] == "Hard"


def test_normalize_summary_and_sections_and_qa():
    summary = normalize_summary({
        "overview": "  Hi ",
        "key_points": ["a", "a", {"text": "b"}],
        "important_concepts": [{"term": "CPU", "definition": "processor"}],
    })
    assert summary == {"overview": "Hi", "key_points": ["a", "b"], "important_concepts": ["CPU: processor"]}
    sections = normalize_sections([{"title": "Intro", "summary": "x", "start_seconds": "12.5"}, {}])
    assert sections == [{"title": "Intro", "content": "x", "start": 12.5}]
    assert normalize_qa([{"front": "f", "back": "b"}]) == [{"question": "f", "answer": "b"}]
    assert normalize_summary(None)["key_points"] == []


def test_cloze_mcqs_have_valid_answers():
    sentences = ["Gradient descent minimises the loss function.", "A neural network has layers."]
    keywords = ["gradient descent", "neural network", "loss function", "layers", "backpropagation"]
    mcqs = build_cloze_mcqs(sentences, keywords)
    assert mcqs
    for q in mcqs:
        assert "_____" in q["question"]
        assert len(q["options"]) == 4
        assert len(set(o.lower() for o in q["options"])) == 4
        assert 0 <= q["answer_index"] < 4
