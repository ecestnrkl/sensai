import re
from typing import Optional, Tuple

import requests

from settings import DEFAULT_TEMPERATURE, DEFAULT_TOP_P, MAX_GENERATION_TOKENS


def detect_api_style(base_url: str) -> str:
    lowered = base_url.lower()
    if "api/chat" in lowered or "11434" in lowered or "ollama" in lowered:
        return "ollama"
    if "v1/chat/completions" in lowered:
        return "openai"
    return "openai"


def normalized_url(base_url: str, style: str) -> str:
    stripped = base_url.rstrip("/")
    if style == "ollama":
        if stripped.endswith("/api/chat"):
            return stripped
        if stripped.endswith("/api"):
            return f"{stripped}/chat"
        return stripped if stripped.endswith("api/chat") else f"{stripped}/api/chat"
    if stripped.endswith("/v1/chat/completions") or stripped.endswith("/chat/completions"):
        return stripped
    if stripped.endswith("/v1"):
        return f"{stripped}/chat/completions"
    return f"{stripped}/v1/chat/completions"


def call_llm(
    endpoint: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = MAX_GENERATION_TOKENS,
) -> Tuple[Optional[str], Optional[str]]:
    style = detect_api_style(endpoint)
    url = normalized_url(endpoint, style)
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    if style == "ollama":
        payload["stream"] = False
        payload["options"] = {
            "num_predict": max_tokens,
            "temperature": DEFAULT_TEMPERATURE,
            "top_p": DEFAULT_TOP_P,
        }
    else:
        payload["max_tokens"] = max_tokens
        payload["temperature"] = DEFAULT_TEMPERATURE
        payload["top_p"] = DEFAULT_TOP_P
    try:
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response else "HTTP error"
        body = ""
        try:
            body = exc.response.text if exc.response else ""
        except Exception:
            body = ""
        extra = ""
        if style == "ollama" and status == 404:
            extra = " (Ollama: Modellname stimmt evtl. nicht; siehe `ollama list` und trage den Namen exakt ein.)"
        return None, f"LLM request failed ({url}): {status} {body}{extra}"
    except Exception as exc:
        return None, f"LLM request failed ({url}): {exc}"

    if style == "ollama":
        content = (data or {}).get("message", {}).get("content")
    else:
        choices = (data or {}).get("choices") or []
        content = None
        if choices:
            content = choices[0].get("message", {}).get("content")
    if not content:
        return None, "LLM response missing content."
    return content.strip(), None


def test_llm_connection(endpoint_url: str, model_name: str) -> str:
    endpoint_url = endpoint_url.strip()
    model_name = model_name.strip()
    if not endpoint_url or not model_name:
        return "Bitte Endpoint-URL und Modellname angeben."
    system_prompt = "You are a concise test assistant."
    user_prompt = "Reply with the single word 'pong'."
    import time

    start = time.time()
    resp, err = call_llm(endpoint_url, model_name, system_prompt, user_prompt, max_tokens=10)
    if err:
        return f"LLM-Test fehlgeschlagen: {err}"
    latency = time.time() - start
    first_line = resp.splitlines()[0] if resp else ""
    return f"LLM ok ({latency:.2f}s): {first_line[:200]}"


def sanitize_llm_output(text: str) -> str:
    cleaned = re.sub(r"\*[^*]+\*", "", text)
    cleaned = re.sub(r"\[[^\]]+\]", "", cleaned)
    # Remove common meta-intros
    cleaned = re.sub(
        r"^(?:here(?:'| i)s my answer:|here(?:'| i)s the answer:|here(?:'| i)s your answer:|"
        r"klar[!:]?|sicher[!:]?|okay[,:]?|ok[,:]?|alright[,:]?|sure[,:]?)\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    return cleaned.strip()


def truncate_response(text: str, max_chars: int = 320) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "…"
