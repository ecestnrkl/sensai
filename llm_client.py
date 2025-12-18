import re
from typing import Any, Dict, List, Optional, Tuple, Union

import requests  # type: ignore[import-untyped]

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
    chat_history: Optional[List[Dict[str, str]]] = None,
) -> Tuple[Optional[str], Optional[str]]:
    style = detect_api_style(endpoint)
    url = normalized_url(endpoint, style)
    messages = [{"role": "system", "content": system_prompt}]
    if chat_history:
        for msg in chat_history:
            role = (msg or {}).get("role")
            content = (msg or {}).get("content")
            if not role or not content:
                continue
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_prompt})
    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
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
        r"klar[!:]?|sicher[!:]?|okay[,:]?|ok[,:]?|alright[,:]?|sure[,:]?|sure thing[,:]?|"
        r"of course[,:]?|absolutely[,:]?|yes[,:]?|yeah[,:]?|oh[,:]?)\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"^(?:thing[,.]?)\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(
        r"^(?:fahrer[-\s]*transkript:|fahrer[-\s]*sagt:|antwortsprache:|driver transcript:|driver says:|response language:)\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    return cleaned.strip()


def scrub_language_leaks(text: str, lang: str) -> str:
    leaks_de = [
        "already",
        "there",
        "sure",
        "ok",
        "okay",
        "right",
        "traffic",
        "driver",
        "bored",
        "jam",
        "stuck",
        "thing",
        "yeah",
        "yes",
    ]
    leaks_en = [
        "schon",
        "doch",
        "nicht",
        "und",
        "aber",
        "bitte",
        "danke",
        "gerne",
        "vielleicht",
        "ruhig",
        "sicher",
        "straße",
        "strasse",
        "fahr",
        "fahrt",
    ]
    lower = text
    if lang == "de":
        for leak in leaks_de:
            lower = re.sub(rf"\b{re.escape(leak)}\b", "", lower, flags=re.IGNORECASE)
        lower = re.sub(r"\b[Aa]lready\b", "", lower)
    else:
        for leak in leaks_en:
            lower = re.sub(rf"\b{re.escape(leak)}\b", "", lower, flags=re.IGNORECASE)
        lower = re.sub(r"\bbitte\b", "", lower, flags=re.IGNORECASE)
    lower = re.sub(r"\s{2,}", " ", lower)
    return lower.strip()


def looks_wrong_language(text: str, lang: str) -> bool:
    english_markers = ["the", "and", "you", "already", "there", "traffic", "road", "car", "drive"]
    german_markers = ["und", "nicht", "schon", "dich", "mir", "dir", "bitte", "danke", "fahrt", "strasse", "straße"]
    lower = text.lower()
    eng_hits = sum(1 for w in english_markers if re.search(rf"\b{w}\b", lower))
    ger_hits = sum(1 for w in german_markers if re.search(rf"\b{w}\b", lower))
    if lang == "de":
        return eng_hits >= 2 and eng_hits > ger_hits
    return ger_hits >= 2 and ger_hits > eng_hits


def _ensure_punctuation(sentence: str) -> str:
    sent = sentence.strip()
    if not sent:
        return ""
    if sent[-1] not in ".!?":
        sent += "."
    return sent


def ensure_two_complete_sentences(text: str, lang: str) -> str:
    normalized = re.sub(r"\.{3,}", ".", text)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    parts = re.split(r"(?<=[.!?])\s+", normalized)
    sentences: List[str] = []
    for part in parts:
        cleaned = part.strip()
        if not cleaned:
            continue
        cleaned = cleaned.rstrip(".!?")
        if cleaned:
            sentences.append(_ensure_punctuation(cleaned))
        if len(sentences) == 2:
            break
    def _fallback(idx: int) -> str:
        if lang == "de":
            return "Bitte konzentriere dich auf die Straße." if idx == 0 else "Bleib ruhig und halte Abstand."
        return "Stay focused on the road." if idx == 0 else "Keep calm and maintain safe distance."
    while len(sentences) < 2:
        sentences.append(_ensure_punctuation(_fallback(len(sentences))))
    return " ".join(sentences[:2])


def truncate_response(text: str, lang: str, max_chars: int = 280, max_words: int = 30) -> str:
    cleaned = scrub_language_leaks(text, lang)
    sentences_text = ensure_two_complete_sentences(cleaned, lang)
    parts = re.split(r"(?<=[.!?])\s+", sentences_text.strip())
    parts = [p.strip() for p in parts if p.strip()]
    if not parts:
        parts = [""]
    if len(parts) < 2:
        parts.append(_ensure_punctuation(parts[0]))
    s1_words = parts[0].split()
    s2_words = parts[1].split()
    total_words = len(s1_words) + len(s2_words)
    if total_words > max_words:
        allowed_s2 = max_words - len(s1_words)
        if allowed_s2 < 4:
            allowed_s2 = 4
        s2_words = s2_words[:allowed_s2]
        parts[1] = _ensure_punctuation(" ".join(s2_words))
    result = f"{parts[0]} {parts[1]}".strip()
    if len(result) > max_chars:
        short_tip = "Bleib aufmerksam und fahr sicher." if lang == "de" else "Stay alert and drive safely."
        result = f"{parts[0]} {short_tip}"
        result = re.sub(r"\s{2,}", " ", result).strip()
    result = scrub_language_leaks(result, lang)
    return ensure_two_complete_sentences(result, lang)


def filter_by_language(text: str, lang: str) -> str:
    return scrub_language_leaks(text, lang)


def rewrite_for_language(endpoint: str, model: str, text: str, lang: str) -> Optional[str]:
    target = "Deutsch" if lang == "de" else "English"
    system_prompt = (
        f"Rewrite the assistant reply in {target} only. Output exactly two short, complete sentences. "
        "No lists, no meta, no quotes."
    )
    user_prompt = f"Rewrite this as two sentences in {target}: {text}"
    rewritten, err = call_llm(endpoint, model, system_prompt, user_prompt, max_tokens=MAX_GENERATION_TOKENS // 2)
    if err or not rewritten:
        return None
    cleaned = sanitize_llm_output(rewritten)
    cleaned = scrub_language_leaks(cleaned, lang)
    return truncate_response(cleaned, lang)
