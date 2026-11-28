from backend.config import Settings
from backend.services import cloud
from backend.services.llm_client import _extract_json, _parse_retry_after
import httpx


class FakeClient:
    def __init__(self):
        self.prompts = []

    def chat_json(self, model, system, user, **kw):
        self.prompts.append(user)
        if "topic sections" in user:
            return {"sections": [{"title": "Part", "start_seconds": 5, "summary": "Stuff."}]}
        return {
            "overview": "Overview.",
            "key_points": ["One.", "Two."],
            "important_concepts": ["Term: def"],
            "keywords": ["alpha", "beta"],
            "sections": [{"title": "Intro", "start_seconds": 0, "summary": "Intro stuff."}],
            "mcqs": [{"question": "Q?", "options": ["a", "b", "c", "d"], "answer_index": 1,
                      "explanation": "because", "difficulty": "Easy"}],
            "short_answers": [{"question": "Why?", "answer": "Because."}],
            "flashcards": [{"question": "F", "answer": "B"}],
        }


def _pipeline(chunk_chars):
    p = cloud.CloudPipeline.__new__(cloud.CloudPipeline)
    p.settings = Settings(llm_chunk_chars=chunk_chars)
    p.client = FakeClient()
    return p


SEGMENTS = [{"start": i * 10, "end": i * 10 + 9, "text": "word " * 50} for i in range(10)]


def test_short_lecture_uses_single_request():
    p = _pipeline(100_000)
    out = p.generate_materials({"segments": SEGMENTS}, "text", lambda *_: None)
    assert len(p.client.prompts) == 1
    assert "[10] word" in p.client.prompts[0]  # timestamps are passed to the model
    assert out["segments"][0]["title"] == "Intro"
    assert out["quiz"]["mcqs"][0]["answer_index"] == 1
    assert out["flashcards"] == [{"question": "F", "answer": "B"}]


def test_long_lecture_is_map_reduced():
    p = _pipeline(600)
    out = p.generate_materials({"segments": SEGMENTS}, "text", lambda *_: None)
    assert len(p.client.prompts) > 2  # several section calls + final call
    assert all(s["title"] == "Part" for s in out["segments"])
    assert out["summary"]["overview"] == "Overview."


def test_extract_json_tolerates_wrapping_text():
    assert _extract_json('Sure! {"a": 1} hope that helps') == {"a": 1}


def test_retry_after_parsing():
    r = httpx.Response(429, text="Please try again in 1m2.5s")
    assert _parse_retry_after(r) == 62.5
    r = httpx.Response(429, headers={"retry-after": "3"})
    assert _parse_retry_after(r) == 3.0


def test_retired_model_gives_actionable_error():
    import pytest
    from backend.services.llm_client import APIError, LLMClient

    def handler(request):
        return httpx.Response(404, json={"error": {"message": "The model `old` does not exist",
                                                   "code": "model_not_found"}})

    client = LLMClient("https://example.test/v1", "key", max_retries=0)
    client._client = httpx.Client(transport=httpx.MockTransport(handler))
    with pytest.raises(APIError, match="'old' is not available"):
        client.chat_json("old", "s", "u")
