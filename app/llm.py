"""Cliente LLM mínimo (httpx). Devuelve (texto, tokens_entrada, tokens_salida)."""
from __future__ import annotations

import httpx

from .config import Settings


class LLMError(Exception):
    pass


def available(s: Settings) -> bool:
    return s.llm_provider in ("anthropic", "openai") and bool(s.llm_api_key)


def complete(s: Settings, system: str, user: str, max_tokens: int) -> tuple[str, int, int]:
    if not available(s):
        raise LLMError("LLM no configurado")
    try:
        if s.llm_provider == "anthropic":
            r = httpx.post(
                (s.llm_base_url or "https://api.anthropic.com") + "/v1/messages",
                headers={"x-api-key": s.llm_api_key, "anthropic-version": "2023-06-01",
                         "content-type": "application/json"},
                json={"model": s.model_name, "max_tokens": max_tokens, "temperature": 0,
                      "system": system, "messages": [{"role": "user", "content": user}]},
                timeout=s.llm_timeout_s)
            r.raise_for_status()
            d = r.json()
            text = "".join(b.get("text", "") for b in d.get("content", []) if b.get("type") == "text")
            u = d.get("usage", {})
            return text.strip(), int(u.get("input_tokens", 0)), int(u.get("output_tokens", 0))
        # openai-compatible
        r = httpx.post(
            (s.llm_base_url or "https://api.openai.com/v1") + "/chat/completions",
            headers={"Authorization": f"Bearer {s.llm_api_key}"},
            json={"model": s.model_name, "max_tokens": max_tokens, "temperature": 0,
                  "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]},
            timeout=s.llm_timeout_s)
        r.raise_for_status()
        d = r.json()
        u = d.get("usage", {})
        return (d["choices"][0]["message"]["content"].strip(),
                int(u.get("prompt_tokens", 0)), int(u.get("completion_tokens", 0)))
    except (httpx.HTTPError, KeyError, IndexError, ValueError) as e:
        raise LLMError(f"{type(e).__name__}") from e
