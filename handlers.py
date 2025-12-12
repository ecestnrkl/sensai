import csv
import datetime
import random
import time
from typing import Dict, List, Optional, Tuple

from audio_io import synthesize_speech, transcribe_audio
from data import SCENARIO_LABEL_TO_ID, SCENARIO_LOOKUP
from llm_client import (
    call_llm,
    filter_by_language,
    looks_wrong_language,
    rewrite_for_language,
    sanitize_llm_output,
    truncate_response,
)
from prompts import base_system_prompt, build_persona_summary, checkin_prompts, user_prompt
from settings import RESULTS_PATH


def resolve_condition_order(order: str) -> Tuple[str, str]:
    if order == "personalized first":
        return ("personalized", "non_personalized")
    if order == "non personalized first":
        return ("non_personalized", "personalized")
    shuffled = random.sample(["personalized", "non_personalized"], k=2)
    return shuffled[0], shuffled[1]


def ensure_results_file():
    if RESULTS_PATH.exists():
        return
    header = [
        "timestamp",
        "participant_id",
        "scenario_id",
        "condition",
        "O",
        "C",
        "E",
        "A",
        "N",
        "dbq_violations",
        "dbq_errors",
        "dbq_lapses",
        "bsss_experience",
        "bsss_thrill",
        "bsss_disinhibition",
        "bsss_boredom",
        "persona_summary",
        "driver_transcript",
        "llm_response",
        "latency_sec",
    ]
    with open(RESULTS_PATH, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)


def append_result_row(row: Dict[str, str]) -> str:
    ensure_results_file()
    with open(RESULTS_PATH, "a", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            [
                row.get("timestamp"),
                row.get("participant_id"),
                row.get("scenario_id"),
                row.get("condition"),
                row.get("O"),
                row.get("C"),
                row.get("E"),
                row.get("A"),
                row.get("N"),
                row.get("dbq_violations"),
                row.get("dbq_errors"),
                row.get("dbq_lapses"),
                row.get("bsss_experience"),
                row.get("bsss_thrill"),
                row.get("bsss_disinhibition"),
                row.get("bsss_boredom"),
                row.get("persona_summary"),
                row.get("driver_transcript"),
                row.get("llm_response"),
                row.get("latency_sec"),
            ]
        )
    return "Saved."


def _history_to_messages(history: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Convert stored history to gr.Chatbot message format (list of role/content dicts)."""
    messages: List[Dict[str, str]] = []
    for msg in history:
        role = (msg or {}).get("role")
        content = (msg or {}).get("content")
        if not role or content is None:
            continue
        messages.append({"role": role, "content": content})
    return messages


def save_condition(condition_key: str, state: dict):
    if not state or not state.get("conditions") or condition_key not in state["conditions"]:
        return "Nothing to save. Run the experiment first."
    condition_info = state["conditions"][condition_key]
    row = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "participant_id": state.get("participant_id", ""),
        "scenario_id": state.get("scenario_id", ""),
        "condition": condition_info.get("condition", condition_key),
        "O": state.get("O"),
        "C": state.get("C"),
        "E": state.get("E"),
        "A": state.get("A"),
        "N": state.get("N"),
        "dbq_violations": state.get("dbq_violations"),
        "dbq_errors": state.get("dbq_errors"),
        "dbq_lapses": state.get("dbq_lapses"),
        "bsss_experience": state.get("bsss_experience"),
        "bsss_thrill": state.get("bsss_thrill"),
        "bsss_disinhibition": state.get("bsss_disinhibition"),
        "bsss_boredom": state.get("bsss_boredom"),
        "persona_summary": state.get("persona_summary", ""),
        "driver_transcript": state.get("transcript", ""),
        "llm_response": condition_info.get("llm_response", ""),
        "latency_sec": condition_info.get("latency", 0.0),
    }
    return append_result_row(row)


def handle_run(
    participant_id: str,
    scenario_label: str,
    o: int,
    c: int,
    e: int,
    a: int,
    n: int,
    dbq_violations: int,
    dbq_errors: int,
    dbq_lapses: int,
    bsss_experience: int,
    bsss_thrill: int,
    bsss_disinhibition: int,
    bsss_boredom: int,
    condition_order: str,
    language: str,
    endpoint_url: str,
    model_name: str,
    audio_path: Optional[str],
    manual_text: str = "",
    state: Optional[dict] = None,
):
    state = state or {}
    if not endpoint_url.strip():
        return (
            "",
            "",
            "Bitte einen LLM Endpoint eintragen (z.B. http://localhost:8000).",
            None,
            "",
            None,
            "",
            "",
            [],
            [],
            {},
        )
    if not model_name.strip():
        return (
            "",
            "",
            "Bitte einen Modellnamen eintragen (z.B. llama-2-7b-chat).",
            None,
            "",
            None,
            "",
            "",
            [],
            [],
            {},
        )
    scenario_id = SCENARIO_LABEL_TO_ID.get(scenario_label, scenario_label)
    if not scenario_id or scenario_id not in SCENARIO_LOOKUP:
        return (
            "",
            "",
            "Select a scenario first.",
            None,
            "",
            None,
            "",
            "",
            [],
            [],
            {},
        )
    existing_history = {}
    for key, history in (state.get("chat_history") or {}).items():
        try:
            existing_history[key] = [dict(msg) for msg in history]  # shallow copy
        except Exception:
            existing_history[key] = []

    manual_text = (manual_text or "").strip()
    transcript_error = None
    detected_lang = None
    if manual_text:
        transcript = manual_text
    else:
        transcript, transcript_error, detected_lang = transcribe_audio(audio_path, language_hint=language)
        if not transcript:
            transcript = SCENARIO_LOOKUP[scenario_id]["text"]
    response_lang = detected_lang if detected_lang in ("en", "de") else language

    persona_summary = build_persona_summary(
        o,
        c,
        e,
        a,
        n,
        dbq_violations,
        dbq_errors,
        dbq_lapses,
        bsss_experience,
        bsss_thrill,
        bsss_disinhibition,
        bsss_boredom,
        response_lang,
    )

    base_system = base_system_prompt(scenario_id, response_lang)

    order = resolve_condition_order(condition_order)
    outputs = []
    condition_data = {}
    prompt_debug: Dict[str, str] = {}

    for idx, condition in enumerate(order, start=1):
        system_prompt = base_system
        if condition == "personalized":
            system_prompt = f"{base_system} Persona hints: {persona_summary}"

        user_prompt_text = user_prompt(transcript, response_lang)
        prompt_debug[f"condition{idx}"] = f"SYSTEM:\n{system_prompt}\n\nUSER:\n{user_prompt_text}"

        start_time = time.time()
        llm_response, llm_error = call_llm(
            endpoint_url,
            model_name,
            system_prompt,
            user_prompt_text,
            chat_history=existing_history.get(condition, []),
        )
        if llm_error:
            error_text = f"{condition.title()} error: {llm_error}"
            outputs.append((error_text, None, 0.0, condition))
            condition_data[f"condition{idx}"] = {
                "condition": condition,
                "llm_response": error_text,
                "audio_path": None,
                "latency": 0.0,
            }
            new_history = list(existing_history.get(condition, []))
            new_history.append({"role": "user", "content": user_prompt_text})
            new_history.append({"role": "assistant", "content": error_text})
            existing_history[condition] = new_history
            continue

        cleaned_response = sanitize_llm_output(llm_response)
        cleaned_response = filter_by_language(cleaned_response, response_lang)
        if looks_wrong_language(cleaned_response, response_lang):
            rewritten = rewrite_for_language(endpoint_url, model_name, cleaned_response, response_lang)
            if rewritten:
                cleaned_response = rewritten
        cleaned_response = truncate_response(cleaned_response, response_lang)
        tts_path, tts_error = synthesize_speech(cleaned_response, response_lang, f"{condition}_{idx}")
        latency = time.time() - start_time

        if tts_error:
            tts_note = (
                "TTS aktuell nicht verfügbar, bitte Text lesen."
                if response_lang == "de"
                else "TTS unavailable right now, please read the text."
            )
            cleaned_response = f"{cleaned_response}\n[{tts_note}]"
            # Keep silent fallback audio if available to avoid UI breakage.
        outputs.append((cleaned_response, tts_path, latency, condition))
        condition_data[f"condition{idx}"] = {
            "condition": condition,
            "llm_response": cleaned_response,
            "audio_path": tts_path,
            "latency": latency,
        }
        new_history = list(existing_history.get(condition, []))
        new_history.append({"role": "user", "content": user_prompt_text})
        new_history.append({"role": "assistant", "content": cleaned_response})
        existing_history[condition] = new_history

    while len(outputs) < 2:
        outputs.append(("", None, 0.0, ""))

    cond1, cond2 = outputs[0], outputs[1]
    state = {
        "participant_id": participant_id,
        "scenario_id": scenario_id,
        "persona_summary": persona_summary,
        "transcript": transcript,
        "response_lang": response_lang,
        "O": o,
        "C": c,
        "E": e,
        "A": a,
        "N": n,
        "dbq_violations": dbq_violations,
        "dbq_errors": dbq_errors,
        "dbq_lapses": dbq_lapses,
        "bsss_experience": bsss_experience,
        "bsss_thrill": bsss_thrill,
        "bsss_disinhibition": bsss_disinhibition,
        "bsss_boredom": bsss_boredom,
        "conditions": condition_data,
        "prompts": prompt_debug,
        "chat_history": existing_history,
    }

    cond1_text = f"{cond1[3].replace('_', ' ').title() or 'Condition 1'}: {cond1[0]}"
    cond2_text = f"{cond2[3].replace('_', ' ').title() or 'Condition 2'}: {cond2[0]}"

    cond1_latency = f"{cond1[2]:.2f}s" if cond1[2] else ""
    cond2_latency = f"{cond2[2]:.2f}s" if cond2[2] else ""

    persona_display = f"{persona_summary}\nCondition order: {', '.join(order)}"
    transcript_display = transcript
    if transcript_error:
        transcript_display = f"{transcript}\n[{transcript_error}]"

    return (
        transcript_display,
        persona_display,
        f"{cond1_text}\nLatency: {cond1_latency}",
        cond1[1],
        f"{cond2_text}\nLatency: {cond2_latency}",
        cond2[1],
        prompt_debug.get("condition1", ""),
        prompt_debug.get("condition2", ""),
        _history_to_messages(existing_history.get(cond1[3], [])),
        _history_to_messages(existing_history.get(cond2[3], [])),
        state,
    )


def handle_checkin(
    participant_id: str,
    scenario_label: str,
    o: int,
    c: int,
    e: int,
    a: int,
    n: int,
    dbq_violations: int,
    dbq_errors: int,
    dbq_lapses: int,
    bsss_experience: int,
    bsss_thrill: int,
    bsss_disinhibition: int,
    bsss_boredom: int,
    language: str,
    endpoint_url: str,
    model_name: str,
):
    if not endpoint_url.strip():
        return "Bitte Endpoint eintragen.", None, ""
    if not model_name.strip():
        return "Bitte Modellnamen eintragen.", None, ""
    scenario_id = SCENARIO_LABEL_TO_ID.get(scenario_label, scenario_label)
    response_lang = language if language in ("en", "de") else "en"
    persona_summary = build_persona_summary(
        o,
        c,
        e,
        a,
        n,
        dbq_violations,
        dbq_errors,
        dbq_lapses,
        bsss_experience,
        bsss_thrill,
        bsss_disinhibition,
        bsss_boredom,
        response_lang,
    )
    system_prompt, user_prompt_text = checkin_prompts(scenario_id, response_lang, persona_summary)
    prompt_debug = f"SYSTEM:\n{system_prompt}\n\nUSER:\n{user_prompt_text}"
    llm_response, llm_error = call_llm(endpoint_url, model_name, system_prompt, user_prompt_text)
    if llm_error:
        return f"Check-in error: {llm_error}", None, prompt_debug
    cleaned = sanitize_llm_output(llm_response)
    cleaned = filter_by_language(cleaned, response_lang)
    if looks_wrong_language(cleaned, response_lang):
        rewritten = rewrite_for_language(endpoint_url, model_name, cleaned, response_lang)
        if rewritten:
            cleaned = rewritten
    cleaned = truncate_response(cleaned, response_lang)
    tts_path, tts_error = synthesize_speech(cleaned, response_lang, "checkin")
    if tts_error:
        tts_note = (
            "TTS aktuell nicht verfügbar, bitte Text lesen."
            if response_lang == "de"
            else "TTS unavailable right now, please read the text."
        )
        cleaned = f"{cleaned}\n[{tts_note}]"
    return cleaned, tts_path, prompt_debug
