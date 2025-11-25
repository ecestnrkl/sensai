import csv
import datetime
import json
import os
import random
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import gradio as gr
import requests
from faster_whisper import WhisperModel
from TTS.api import TTS
try:
    import torch
    from torch.serialization import add_safe_globals
    from TTS.tts.configs.xtts_config import XttsConfig
except Exception:  # pragma: no cover - defensive import
    torch = None  # type: ignore
    add_safe_globals = None  # type: ignore
    XttsConfig = None  # type: ignore


BASE_DIR = Path(__file__).parent
SCENARIO_PATH = BASE_DIR / "scenarios.json"
PERSONA_RULES_PATH = BASE_DIR / "persona_rules.json"
RESULTS_PATH = BASE_DIR / "results.csv"
SURVEY_ITEMS_PATH = BASE_DIR / "survey_items.csv"
TMP_DIR = BASE_DIR / "tmp_audio"
TMP_DIR.mkdir(exist_ok=True)

# Lazily loaded models so the app can start quickly.
whisper_model: Optional[WhisperModel] = None
tts_model: Optional[TTS] = None
tts_default_speaker: Optional[str] = None

MAX_GENERATION_TOKENS = 200  # keep generations short to avoid long waits
DEFAULT_TEMPERATURE = 0.6
DEFAULT_TOP_P = 0.9

def load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


SCENARIOS: List[Dict[str, str]] = load_json(SCENARIO_PATH)
PERSONA_RULES: Dict[str, str] = load_json(PERSONA_RULES_PATH)
SCENARIO_LOOKUP = {item["id"]: item for item in SCENARIOS}
SCENARIO_LABEL_TO_ID = {
    f"{item['title']} ({item['id']})": item["id"] for item in SCENARIOS
}
SURVEY_ITEMS_SNIPPET = ""
SURVEY_ITEMS: List[Dict[str, str]] = []


def load_survey_items(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    items: List[Dict[str, str]] = []
    try:
        with open(path, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                item_text = (row.get("Item_Text") or "").strip()
                if not item_text:
                    continue
                items.append({
                    "Section": (row.get("Section") or "").strip(),
                    "Item_Number": (row.get("Item_Number") or "").strip(),
                    "Item_Text": item_text,
                    "Scale": (row.get("Scale") or "").strip(),
                    "Source": (row.get("Source") or "").strip(),
                    "Construct": (row.get("Construct") or "").strip(),
                    "Note": (row.get("Note") or "").strip(),
                })
    except Exception:
        return []
    return items


def build_survey_items_snippet(items: List[Dict[str, str]]) -> str:
    snippet_lines: List[str] = []
    for item in items:
        label = f"{item.get('Section', '')} {item.get('Item_Number', '')}".strip()
        item_text = item.get("Item_Text", "")
        scale = item.get("Scale", "")
        line = f"{label}: {item_text}"
        if scale:
            line += f" (Scale: {scale})"
        snippet_lines.append(line)
    return "\n".join(snippet_lines)


SURVEY_ITEMS = load_survey_items(SURVEY_ITEMS_PATH)
SURVEY_ITEMS_SNIPPET = build_survey_items_snippet(SURVEY_ITEMS)


def get_whisper() -> WhisperModel:
    global whisper_model
    if whisper_model is None:
        whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
    return whisper_model


def get_tts() -> Tuple[TTS, Optional[str]]:
    global tts_model, tts_default_speaker
    if tts_model is None:
        try:
            # Torch >=2.6 sets weights_only=True default; allowlist XTTS config class.
            if add_safe_globals and XttsConfig:
                try:
                    add_safe_globals([XttsConfig])
                except Exception:
                    pass
            tts_model = TTS(
                model_name="tts_models/multilingual/multi-dataset/xtts_v2",
                progress_bar=False,
                gpu=False,
            )
        except ImportError as exc:
            msg = str(exc)
            if "BeamSearchScorer" in msg or "transformers" in msg:
                raise RuntimeError(
                    "TTS-Init fehlgeschlagen: Bitte `pip install \"transformers<4.46\"` im .venv ausfuehren."
                ) from exc
            if "Weights only load failed" in msg or "weights_only" in msg:
                raise RuntimeError(
                    "TTS-Init fehlgeschlagen (weights_only). Wenn das Warmup scheitert, versuche `pip install torch==2.5.1` im .venv "
                    "oder stelle sicher, dass die XTTS-Checkpoint-Datei aus vertrauenswuerdiger Quelle stammt."
                ) from exc
            raise
        # Try to pick a default speaker from the speaker_manager (XTTS is multi-speaker).
        try:
            sm = tts_model.synthesizer.tts_model.speaker_manager  # type: ignore[attr-defined]
            if sm and getattr(sm, "speakers", None):
                names = list(sm.speakers.keys())
                if names:
                    tts_default_speaker = names[0]
        except Exception:
            tts_default_speaker = None
        env_speaker = os.getenv("TTS_SPEAKER_NAME")
        if env_speaker:
            tts_default_speaker = env_speaker
    return tts_model, tts_default_speaker


def build_persona_summary(o: int, c: int, e: int, a: int, n: int) -> str:
    summary_parts = [PERSONA_RULES.get("default", "")]
    if n >= 4:
        summary_parts.append(PERSONA_RULES.get("high_neuroticism", ""))
    if e >= 4:
        summary_parts.append(PERSONA_RULES.get("high_extraversion", ""))
    if a >= 4:
        summary_parts.append(PERSONA_RULES.get("high_agreeableness", ""))
    if a <= 2:
        summary_parts.append(PERSONA_RULES.get("low_agreeableness", ""))
    return " ".join([p.strip() for p in summary_parts if p]).strip()


def transcribe_audio(audio_path: Optional[str]) -> Tuple[str, Optional[str]]:
    if not audio_path or not Path(audio_path).exists():
        return "", "No audio captured. Using scenario text instead."
    try:
        model = get_whisper()
        segments, _ = model.transcribe(audio_path, beam_size=5, language=None)
        text = " ".join([seg.text.strip() for seg in segments]).strip()
        return text, None
    except Exception as exc:  # pragma: no cover - runtime safeguard
        return "", f"Transcription failed: {exc}"


def resolve_condition_order(order: str) -> List[str]:
    if order == "personalized first":
        return ["personalized", "non_personalized"]
    if order == "non personalized first":
        return ["non_personalized", "personalized"]
    return random.sample(["personalized", "non_personalized"], k=2)


def detect_api_style(base_url: str) -> str:
    lowered = base_url.lower()
    if "api/chat" in lowered or "11434" in lowered or "ollama" in lowered:
        return "ollama"
    if "v1/chat/completions" in lowered:
        return "openai"
    return "openai"


def normalized_url(base_url: str, style: str) -> str:
    stripped = base_url.rstrip("/")
    # Normalize common user inputs so we don't end up with duplicated paths
    # like /v1/v1/chat/completions when someone pastes a base URL ending in /v1.
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
        # Avoid streaming; Ollama streams by default, which breaks simple json parsing.
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
    except requests.HTTPError as exc:  # pragma: no cover - runtime safeguard
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
    except Exception as exc:  # pragma: no cover - runtime safeguard
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
    start = time.time()
    resp, err = call_llm(endpoint_url, model_name, system_prompt, user_prompt, max_tokens=10)
    if err:
        return f"LLM-Test fehlgeschlagen: {err}"
    latency = time.time() - start
    first_line = resp.splitlines()[0] if resp else ""
    return f"LLM ok ({latency:.2f}s): {first_line[:200]}"


def synthesize_speech(text: str, language: str, tag: str) -> Tuple[Optional[str], Optional[str]]:
    tts, speaker = get_tts()
    out_path = TMP_DIR / f"{tag}_{uuid.uuid4().hex}.wav"
    tts_kwargs = {"text": text, "language": language, "file_path": str(out_path)}
    # XTTS v2 ist multi-speaker; falls nichts gesetzt ist, nimm Default-Speaker aus speaker_manager.
    if speaker:
        tts_kwargs["speaker"] = speaker
    else:
        try:
            sm = tts.synthesizer.tts_model.speaker_manager  # type: ignore[attr-defined]
            if sm and getattr(sm, "speakers", None):
                names = list(sm.speakers.keys())
                if names:
                    tts_kwargs["speaker"] = names[0]
        except Exception:
            pass
    speaker_wav = os.getenv("TTS_SPEAKER_WAV")
    if speaker_wav and Path(speaker_wav).exists():
        tts_kwargs["speaker_wav"] = speaker_wav
    try:
        tts.tts_to_file(**tts_kwargs)
        return str(out_path), None
    except Exception as exc:  # pragma: no cover - runtime safeguard
        return None, f"TTS error: {exc}"


def warm_up_models() -> str:
    msgs = []
    try:
        get_whisper()
        msgs.append("Whisper ok")
    except Exception as exc:  # pragma: no cover - runtime safeguard
        msgs.append(f"Whisper Fehler: {exc}")
    try:
        get_tts()
        msgs.append("XTTS ok (erstes Laden kann >1min dauern)")
    except Exception as exc:  # pragma: no cover - runtime safeguard
        msgs.append(f"TTS Fehler: {exc}")
    return " | ".join(msgs)


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
        "persona_summary",
        "driver_transcript",
        "llm_response",
        "empathy",
        "relevance",
        "acceptance",
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
                row.get("persona_summary"),
                row.get("driver_transcript"),
                row.get("llm_response"),
                row.get("empathy"),
                row.get("relevance"),
                row.get("acceptance"),
                row.get("latency_sec"),
            ]
        )
    return "Saved."


def handle_run(
    survey_state: Optional[dict],
    participant_id: str,
    scenario_label: str,
    o: int,
    c: int,
    e: int,
    a: int,
    n: int,
    condition_order: str,
    language: str,
    endpoint_url: str,
    model_name: str,
    audio_path: Optional[str],
):
    if not endpoint_url.strip():
        return (
            "",
            "",
            "Bitte einen LLM Endpoint eintragen (z.B. http://localhost:8000).",
            None,
            "",
            None,
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
            {},
        )
    if not survey_state or not survey_state.get("survey_completed"):
        message = "Bitte erst die Pre-Test-Umfrage ausfuellen."
        return (
            message,
            "",
            "",
            None,
            "",
            None,
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
            {},
        )
    scenario = SCENARIO_LOOKUP.get(scenario_id)
    persona_summary = build_persona_summary(o, c, e, a, n)

    transcript, transcript_error = transcribe_audio(audio_path)
    if not transcript:
        transcript = scenario["text"]

    survey_answers_text = ""
    if survey_state and survey_state.get("survey_answers"):
        pairs = [
            f"{key}: {val}"
            for key, val in survey_state["survey_answers"].items()
            if val not in (None, "")
        ]
        if pairs:
            survey_answers_text = "Participant survey responses:\n" + "\n".join(pairs)

    survey_info = (
        f"Baseline questionnaire items shown earlier:\n{SURVEY_ITEMS_SNIPPET}"
        if SURVEY_ITEMS_SNIPPET
        else ""
    )
    base_system = (
        "You are a vehicle assistant. Keep responses under three sentences. "
        "Prioritize safety guidance before emotional support. "
        f"Scenario context: {scenario['text']}\n"
        f"{survey_info}\n"
        f"{survey_answers_text}"
    )

    order = resolve_condition_order(condition_order)
    outputs = []
    condition_data = {}

    for idx, condition in enumerate(order, start=1):
        system_prompt = base_system
        if condition == "personalized":
            system_prompt = f"{base_system} Persona hints: {persona_summary}"

        user_prompt = (
            f"Driver transcript: {transcript}. "
            "Offer clear and safe next steps with empathy if appropriate."
        )

        start_time = time.time()
        llm_response, llm_error = call_llm(endpoint_url, model_name, system_prompt, user_prompt)
        if llm_error:
            error_text = f"{condition.title()} error: {llm_error}"
            outputs.append((error_text, None, 0.0, condition))
            condition_data[f"condition{idx}"] = {
                "condition": condition,
                "llm_response": error_text,
                "audio_path": None,
                "latency": 0.0,
            }
            continue

        tts_path, tts_error = synthesize_speech(llm_response, language, f"{condition}_{idx}")
        latency = time.time() - start_time

        if tts_error:
            llm_response = f"{llm_response}\n[TTS failed: {tts_error}]"
            tts_path = None
        outputs.append((llm_response, tts_path, latency, condition))
        condition_data[f"condition{idx}"] = {
            "condition": condition,
            "llm_response": llm_response,
            "audio_path": tts_path,
            "latency": latency,
        }

    # Pad outputs in case of errors.
    while len(outputs) < 2:
        outputs.append(("", None, 0.0, ""))

    cond1, cond2 = outputs[0], outputs[1]
    state = {
        "participant_id": participant_id,
        "scenario_id": scenario_id,
        "persona_summary": persona_summary,
        "transcript": transcript,
        "O": o,
        "C": c,
        "E": e,
        "A": a,
        "N": n,
        "conditions": condition_data,
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
        state,
    )


def save_condition(condition_key: str, scores: Dict[str, int], state: dict):
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
        "persona_summary": state.get("persona_summary", ""),
        "driver_transcript": state.get("transcript", ""),
        "llm_response": condition_info.get("llm_response", ""),
        "empathy": scores.get("empathy"),
        "relevance": scores.get("relevance"),
        "acceptance": scores.get("acceptance"),
        "latency_sec": condition_info.get("latency", 0.0),
    }
    return append_result_row(row)


def build_interface():
    scenario_choices = [(f"{s['title']} ({s['id']})", s["id"]) for s in SCENARIOS]
    scenario_label_map = {label: sid for label, sid in scenario_choices}

    with gr.Blocks(title="Audio Personality Prompting Prototype") as demo:
        gr.Markdown("# Audio Personality Prompting Prototype")
        with gr.Row():
            participant_id = gr.Textbox(label="Participant ID", placeholder="P001")
            endpoint_url = gr.Textbox(label="LLM Endpoint URL", value="http://localhost:11434")
            model_name = gr.Textbox(label="Model Name", value="llama2:7b-chat")
        with gr.Row():
            llm_status = gr.Textbox(
                label="LLM Status / Troubleshooting",
                value="Trage Endpoint & Modell ein und druecke 'LLM Verbindung testen'.",
                interactive=False,
            )
            llm_test_btn = gr.Button("LLM Verbindung testen", variant="secondary")
        with gr.Row():
            warmup_status = gr.Textbox(
                label="Modell-Warmup (Whisper + TTS)",
                value="Erster TTS/Whisper-Download kann 1-2 Minuten dauern. Jetzt vorladen, um spaetere Pausen zu vermeiden.",
                interactive=False,
            )
            warmup_btn = gr.Button("Warmup starten", variant="secondary")
        with gr.Tab("Pre-Test Survey"):
            gr.Markdown("Bitte die Umfrage vor dem Test ausfuellen.")
            survey_components = []
            for item in SURVEY_ITEMS:
                label = f"{item.get('Item_Number', '')} - {item.get('Item_Text', '')}"
                scale = (item.get("Scale") or "").lower()
                raw_scale = item.get("Scale") or ""
                if "multiple choice" in scale and ":" in raw_scale:
                    options_part = raw_scale.split(":", 1)[1]
                    options = [opt.strip() for opt in options_part.split("/") if opt.strip()]
                    comp = gr.Dropdown(choices=options, label=label)
                elif "7-punkt" in scale:
                    comp = gr.Slider(1, 7, step=1, label=label, value=4)
                elif "5-punkt" in scale:
                    comp = gr.Slider(1, 5, step=1, label=label, value=3)
                else:
                    comp = gr.Textbox(label=label)
                survey_components.append(comp)
            save_survey = gr.Button("Survey speichern", variant="primary")
            survey_status = gr.Textbox(label="Survey Status", interactive=False)

        with gr.Tab("Experiment"):
            with gr.Row():
                scenario_dropdown = gr.Dropdown(
                    choices=[choice[0] for choice in scenario_choices],
                    value=scenario_choices[0][0] if scenario_choices else None,
                    label="Scenario",
                )
                default_text = (
                    SCENARIO_LOOKUP[scenario_choices[0][1]]["text"] if scenario_choices else ""
                )
                scenario_text = gr.Textbox(
                    label="Scenario text", interactive=False, lines=3, value=default_text
                )
            scenario_dropdown.change(
                lambda label: SCENARIO_LOOKUP[scenario_label_map.get(label, "")]["text"]
                if label in scenario_label_map
                else "",
                inputs=scenario_dropdown,
                outputs=scenario_text,
            )

        with gr.Row():
            condition_order = gr.Radio(
                ["random", "personalized first", "non personalized first"],
                value="random",
                label="Condition order",
            )
            language = gr.Radio(["en", "de"], value="en", label="TTS language (Coqui XTTS v2)")

        gr.Markdown("### Big Five (1-5)")
        with gr.Row():
            o = gr.Slider(1, 5, value=3, step=1, label="Openness (O)")
            c = gr.Slider(1, 5, value=3, step=1, label="Conscientiousness (C)")
            e_slider = gr.Slider(1, 5, value=3, step=1, label="Extraversion (E)")
            a_slider = gr.Slider(1, 5, value=3, step=1, label="Agreeableness (A)")
            n_slider = gr.Slider(1, 5, value=3, step=1, label="Neuroticism (N)")

        audio_in = gr.Audio(
            sources=["microphone"],
            type="filepath",
            label="Microphone (push to talk)",
            format="wav",
        )

        run_button = gr.Button("Run both conditions", variant="primary")

        transcript_box = gr.Textbox(label="Driver transcript", lines=3)
        persona_box = gr.Textbox(label="Persona summary", lines=3)

        with gr.Row():
            cond1_text = gr.Textbox(label="Condition 1 response", lines=4)
            cond1_audio = gr.Audio(label="Condition 1 TTS", type="filepath")
        with gr.Row():
            cond2_text = gr.Textbox(label="Condition 2 response", lines=4)
            cond2_audio = gr.Audio(label="Condition 2 TTS", type="filepath")

        state = gr.State({})
        survey_state = gr.State({})

        llm_test_btn.click(
            lambda url, model: test_llm_connection(url, model),
            inputs=[endpoint_url, model_name],
            outputs=llm_status,
        )
        warmup_btn.click(
            lambda: warm_up_models(),
            inputs=None,
            outputs=warmup_status,
        )

        def save_survey_responses(*responses):
            answers = {item.get("Item_Number", f"Q{idx+1}"): resp for idx, (item, resp) in enumerate(zip(SURVEY_ITEMS, responses))}
            return {"survey_completed": True, "survey_answers": answers}, "Survey gespeichert."

        save_survey.click(
            save_survey_responses,
            inputs=survey_components,
            outputs=[survey_state, survey_status],
        )

        run_button.click(
            handle_run,
            inputs=[
                survey_state,
                participant_id,
                scenario_dropdown,
                o,
                c,
                e_slider,
                a_slider,
                n_slider,
                condition_order,
                language,
                endpoint_url,
                model_name,
                audio_in,
            ],
            outputs=[
                transcript_box,
                persona_box,
                cond1_text,
                cond1_audio,
                cond2_text,
                cond2_audio,
                state,
            ],
        )

        gr.Markdown("### Ratings (1-7)")
        with gr.Row():
            empathy1 = gr.Slider(1, 7, step=1, value=4, label="Condition 1 empathy")
            relevance1 = gr.Slider(1, 7, step=1, value=4, label="Condition 1 relevance")
            acceptance1 = gr.Slider(1, 7, step=1, value=4, label="Condition 1 acceptance")
        save1 = gr.Button("Save Condition 1")
        save1_status = gr.Textbox(label="Save status (Condition 1)", interactive=False)

        with gr.Row():
            empathy2 = gr.Slider(1, 7, step=1, value=4, label="Condition 2 empathy")
            relevance2 = gr.Slider(1, 7, step=1, value=4, label="Condition 2 relevance")
            acceptance2 = gr.Slider(1, 7, step=1, value=4, label="Condition 2 acceptance")
        save2 = gr.Button("Save Condition 2")
        save2_status = gr.Textbox(label="Save status (Condition 2)", interactive=False)

        save1.click(
            lambda em, rel, acc, st: save_condition("condition1", {"empathy": em, "relevance": rel, "acceptance": acc}, st),
            inputs=[empathy1, relevance1, acceptance1, state],
            outputs=save1_status,
        )
        save2.click(
            lambda em, rel, acc, st: save_condition("condition2", {"empathy": em, "relevance": rel, "acceptance": acc}, st),
            inputs=[empathy2, relevance2, acceptance2, state],
            outputs=save2_status,
        )

    return demo


if __name__ == "__main__":
    interface = build_interface()
    interface.launch()
