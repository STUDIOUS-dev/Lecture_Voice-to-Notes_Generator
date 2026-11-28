"""
Minimal client for OpenAI-compatible APIs (Groq by default).

Implements just the two endpoints we need — chat completions (JSON mode) and
audio transcriptions — with retries that respect rate-limit headers, so
free-tier limits slow the pipeline down instead of failing it.
"""

import json
import logging
import random
import re
import time
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

RETRYABLE_STATUS = {408, 409, 429, 500, 502, 503, 504}


class APIError(RuntimeError):
    """A non-retryable or exhausted API failure, with a user-safe message."""


def _parse_retry_after(response: httpx.Response) -> float | None:
    value = response.headers.get("retry-after")
    if value:
        try:
            return float(value)
        except ValueError:
            pass
    # Groq also reports e.g. "Please try again in 7.66s" in the error body
    match = re.search(r"try again in (?:(\d+)m)?([\d.]+)s", response.text or "")
    if match:
        return int(match.group(1) or 0) * 60 + float(match.group(2))
    return None


class LLMClient:
    def __init__(self, base_url: str, api_key: str, timeout: float = 300.0, max_retries: int = 6):
        if not api_key:
            raise APIError("No API key configured. Set GROQ_API_KEY (or LLM_API_KEY).")
        self.base_url = base_url.rstrip("/")
        self.max_retries = max_retries
        self._client = httpx.Client(
            timeout=timeout,
            headers={"Authorization": f"Bearer {api_key}"},
        )

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        url = f"{self.base_url}{path}"
        for attempt in range(self.max_retries + 1):
            try:
                response = self._client.request(method, url, **kwargs)
            except httpx.TransportError as exc:
                if attempt == self.max_retries:
                    raise APIError(f"Could not reach the AI service: {exc}") from exc
                delay = min(2 ** attempt, 30)
            else:
                if response.status_code < 400:
                    return response
                if response.status_code in (401, 403):
                    raise APIError("The AI service rejected the API key. Check GROQ_API_KEY.")
                if response.status_code == 404 and "model" in response.text.lower():
                    logger.error("Model not found: %s", response.text[:500])
                    model = (kwargs.get("json") or kwargs.get("data") or {}).get("model", "")
                    raise APIError(
                        f"The AI model '{model}' is not available from the provider. "
                        "Set LLM_MODEL (or TRANSCRIPTION_MODEL) to a current model."
                    )
                if response.status_code not in RETRYABLE_STATUS or attempt == self.max_retries:
                    logger.error("API error %s: %s", response.status_code, response.text[:1000])
                    raise APIError(
                        f"The AI service returned an error (HTTP {response.status_code})."
                    )
                delay = _parse_retry_after(response) or min(2 ** attempt, 30)
            delay = min(delay, 90) + random.uniform(0, 1)
            logger.warning("API request to %s failed, retrying in %.1fs", path, delay)
            for file_tuple in (kwargs.get("files") or {}).values():
                # rewind file handles so the retry re-sends the whole upload
                handle = file_tuple[1] if isinstance(file_tuple, tuple) else None
                if hasattr(handle, "seek"):
                    handle.seek(0)
            time.sleep(delay)
        raise APIError("The AI service is unavailable. Please try again later.")

    def chat_json(self, model: str, system: str, user: str, temperature: float = 0.3,
                  max_tokens: int = 4096) -> dict[str, Any]:
        """Run a chat completion that must return a JSON object."""
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
        }
        last_error: Exception | None = None
        for _ in range(2):  # one extra attempt if the model returns malformed JSON
            data = self._request("POST", "/chat/completions", json=payload).json()
            content = data["choices"][0]["message"]["content"] or ""
            try:
                return _extract_json(content)
            except ValueError as exc:
                last_error = exc
                logger.warning("Model returned invalid JSON, retrying")
        raise APIError("The AI model returned an unreadable response.") from last_error

    def transcribe(self, model: str, audio_path: Path, language: str | None = None) -> dict[str, Any]:
        """Transcribe an audio file; returns {'text', 'segments', 'language'}."""
        data = {"model": model, "response_format": "verbose_json", "temperature": "0"}
        if language:
            data["language"] = language
        with open(audio_path, "rb") as fh:
            response = self._request(
                "POST", "/audio/transcriptions",
                data=data,
                files={"file": (audio_path.name, fh, "audio/mpeg")},
            )
        return response.json()

    def close(self) -> None:
        self._client.close()


def _extract_json(content: str) -> dict[str, Any]:
    content = content.strip()
    try:
        result = json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if not match:
            raise ValueError("No JSON object found")
        result = json.loads(match.group(0))
    if not isinstance(result, dict):
        raise ValueError("Expected a JSON object")
    return result
