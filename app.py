import gradio as gr

from audio_io import warm_up_models
from data import SCENARIO_LABEL_TO_ID, SCENARIO_LOOKUP, get_scenario_text
from handlers import handle_checkin, handle_run, save_condition
from llm_client import test_llm_connection
from settings import DEFAULT_ENDPOINT, DEFAULT_MODEL, LANG_CHOICES

CUSTOM_CSS = """
/* Subtle condition coloring for response boxes */
.cond-personalized {
  --input-background-fill: rgba(46, 204, 113, 0.12);
}

.cond-nonpersonalized {
  --input-background-fill: rgba(52, 152, 219, 0.12);
}

.cond-response textarea,
.cond-response input {
  transition: background-color 0.2s ease-in-out;
}

.cond-personalized textarea,
.cond-personalized input {
  background-color: rgba(46, 204, 113, 0.12) !important;
}

.cond-nonpersonalized textarea,
.cond-nonpersonalized input {
  background-color: rgba(52, 152, 219, 0.12) !important;
}
"""

TRANSLATIONS = {
    "de": {
        "participant_id": "Teilnehmer-ID",
        "endpoint": "LLM Endpoint URL",
        "model": "Modellname",
        "lang_label": "UI/Antwort-Sprache",
        "llm_status_value": "Trage Endpoint & Modell ein und druecke 'LLM Verbindung testen'.",
        "warmup_value": "Erster TTS/Whisper-Download kann 1-2 Minuten dauern. Jetzt vorladen, um spaetere Pausen zu vermeiden.",
        "scenario_label": "Szenario",
        "scenario_text_label": "Szenario-Text",
        "condition_order_label": "Reihenfolge",
        "big_five": ["Offenheit (O)", "Gewissenhaftigkeit (C)", "Extraversion (E)", "Verträglichkeit (A)", "Neurotizismus (N)"],
        "dbq": ["Verstöße", "Fehler", "Unaufmerksamkeiten"],
        "bsss": ["Erfahrungs-Suche", "Thrill & Adventure", "Enthemmung", "Langeweile-Anfälligkeit"],
        "erq": ["Cognitive Reappraisal", "Expressive Suppression"],
        "audio_label": "Mikrofon (Push-to-talk)",
        "run_button": "Beide Bedingungen ausführen",
        "transcript_label": "Fahrer-Transkript",
        "persona_label": "Persona-Zusammenfassung",
        "cond1_text": "Condition 1 Antwort",
        "cond1_audio": "Condition 1 TTS",
        "cond2_text": "Condition 2 Antwort",
        "cond2_audio": "Condition 2 TTS",
        "prompt1": "Condition 1 Prompt",
        "prompt2": "Condition 2 Prompt",
        "text_input": "Textfeld (optional statt Spracheingabe)",
        "text_placeholder": "Hier tippen, wenn du nicht sprechen möchtest.",
        "chat1": "Gesprächsverlauf (Condition 1)",
        "chat2": "Gesprächsverlauf (Condition 2)",
        "checkin_button": "Check-in auslösen",
        "checkin_text": "Check-in Text",
        "checkin_audio": "Check-in TTS",
        "checkin_prompt": "Check-in Prompt (Debug)",
        "save1": "Condition 1 speichern",
        "save2": "Condition 2 speichern",
        "save1_status": "Speicherstatus (Condition 1)",
        "save2_status": "Speicherstatus (Condition 2)",
    },
    "en": {
        "participant_id": "Participant ID",
        "endpoint": "LLM Endpoint URL",
        "model": "Model Name",
        "lang_label": "UI/Response Language",
        "llm_status_value": "Enter endpoint & model then click 'Test LLM Connection'.",
        "warmup_value": "First TTS/Whisper download can take 1-2 minutes. Warm up now to avoid pauses.",
        "scenario_label": "Scenario",
        "scenario_text_label": "Scenario text",
        "condition_order_label": "Condition order",
        "big_five": ["Openness (O)", "Conscientiousness (C)", "Extraversion (E)", "Agreeableness (A)", "Neuroticism (N)"],
        "dbq": ["Violations", "Errors", "Lapses"],
        "bsss": ["Experience Seeking", "Thrill & Adventure", "Disinhibition", "Boredom Susceptibility"],
        "erq": ["Cognitive Reappraisal", "Expressive Suppression"],
        "audio_label": "Microphone (push to talk)",
        "run_button": "Run both conditions",
        "transcript_label": "Driver transcript",
        "persona_label": "Persona summary",
        "cond1_text": "Condition 1 response",
        "cond1_audio": "Condition 1 TTS",
        "cond2_text": "Condition 2 response",
        "cond2_audio": "Condition 2 TTS",
        "prompt1": "Condition 1 prompt",
        "prompt2": "Condition 2 prompt",
        "text_input": "Type instead of speaking (optional)",
        "text_placeholder": "Type here if you do not want to use the microphone.",
        "chat1": "Conversation (Condition 1)",
        "chat2": "Conversation (Condition 2)",
        "checkin_button": "Trigger Check-in",
        "checkin_text": "Check-in text",
        "checkin_audio": "Check-in TTS",
        "checkin_prompt": "Check-in prompt (Debug)",
        "save1": "Save Condition 1",
        "save2": "Save Condition 2",
        "save1_status": "Save status (Condition 1)",
        "save2_status": "Save status (Condition 2)",
    },
}


def build_interface():
    scenario_choices = [(f"{s['title']} ({s['id']})", s["id"]) for s in SCENARIO_LOOKUP.values()]
    scenario_label_map = {label: sid for label, sid in scenario_choices}

    default_lang = "en"
    tr = TRANSLATIONS[default_lang]
    with gr.Blocks(title="Audio Personality Prompting Prototype") as demo:
        demo.css = CUSTOM_CSS
        gr.Markdown("# Audio Personality Prompting Prototype")
        with gr.Row():
            participant_id = gr.Textbox(label=tr["participant_id"], placeholder="P001")
            endpoint_url = gr.Textbox(label=tr["endpoint"], value=DEFAULT_ENDPOINT)
            model_name = gr.Textbox(label=tr["model"], value=DEFAULT_MODEL)
            language = gr.Radio(LANG_CHOICES, value=default_lang, label=tr["lang_label"])
        with gr.Row():
            llm_status = gr.Textbox(
                label="LLM Status / Troubleshooting",
                value=tr["llm_status_value"],
                interactive=False,
            )
            llm_test_btn = gr.Button("LLM Verbindung testen", variant="secondary")
        with gr.Row():
            warmup_status = gr.Textbox(
                label="Modell-Warmup (Whisper + TTS)",
                value=tr["warmup_value"],
                interactive=False,
            )
            warmup_btn = gr.Button("Warmup starten", variant="secondary")

        with gr.Tab("Experiment"):
            with gr.Row():
                scenario_dropdown = gr.Dropdown(
                    choices=[choice[0] for choice in scenario_choices],
                    value=scenario_choices[0][0] if scenario_choices else None,
                    label=tr["scenario_label"],
                )
                default_text = (
                    get_scenario_text(scenario_choices[0][1], default_lang) if scenario_choices else ""
                )
                scenario_text = gr.Textbox(
                    label=tr["scenario_text_label"], interactive=False, lines=3, value=default_text
                )
            scenario_dropdown.change(
                lambda label, lang: get_scenario_text(scenario_label_map.get(label, ""), lang)
                if label in scenario_label_map
                else "",
                inputs=[scenario_dropdown, language],
                outputs=scenario_text,
            )
            with gr.Row():
                condition_order = gr.Radio(
                    ["random", "personalized first", "non personalized first"],
                    value="random",
                    label=tr["condition_order_label"],
                )

            gr.Markdown("### Big Five (1-5)")
            with gr.Row():
                o = gr.Slider(1, 5, value=3, step=1, label=tr["big_five"][0])
                c = gr.Slider(1, 5, value=3, step=1, label=tr["big_five"][1])
                e_slider = gr.Slider(1, 5, value=3, step=1, label=tr["big_five"][2])
                a_slider = gr.Slider(1, 5, value=3, step=1, label=tr["big_five"][3])
                n_slider = gr.Slider(1, 5, value=3, step=1, label=tr["big_five"][4])
            gr.Markdown("### Mini DBQ (1-5)")
            with gr.Row():
                dbq_violations = gr.Slider(1, 5, value=3, step=1, label=tr["dbq"][0])
                dbq_errors = gr.Slider(1, 5, value=3, step=1, label=tr["dbq"][1])
                dbq_lapses = gr.Slider(1, 5, value=3, step=1, label=tr["dbq"][2])
            gr.Markdown("### Brief Sensation Seeking Scale (1-5)")
            with gr.Row():
                bsss_experience = gr.Slider(1, 5, value=3, step=1, label=tr["bsss"][0])
                bsss_thrill = gr.Slider(1, 5, value=3, step=1, label=tr["bsss"][1])
                bsss_disinhibition = gr.Slider(1, 5, value=3, step=1, label=tr["bsss"][2])
                bsss_boredom = gr.Slider(1, 5, value=3, step=1, label=tr["bsss"][3])

            gr.Markdown("### Emotion Regulation Questionnaire (1-7)")
            with gr.Row():
                erq_reappraisal = gr.Slider(1, 7, value=3, step=1, label=tr["erq"][0])
                erq_suppression = gr.Slider(1, 7, value=3, step=1, label=tr["erq"][1])

            gr.Markdown("### Gesprächseinstieg (Check-in)")
            with gr.Row():
                checkin_button = gr.Button(tr["checkin_button"], variant="secondary")
                checkin_status = gr.Textbox(label=tr["checkin_text"], lines=2)
                checkin_audio = gr.Audio(label=tr["checkin_audio"], type="filepath")
            checkin_prompt_box = gr.Textbox(label=tr["checkin_prompt"], lines=3)

            gr.Markdown("### Eingabe")
            with gr.Row():
                audio_in = gr.Audio(
                    sources=["microphone"],
                    type="filepath",
                    label=tr["audio_label"],
                    format="wav",
                )
                manual_text = gr.Textbox(
                    label=tr["text_input"],
                    lines=4,
                    placeholder=tr["text_placeholder"],
                )

            run_button = gr.Button(tr["run_button"], variant="primary")

            transcript_box = gr.Textbox(label=tr["transcript_label"], lines=3)
            persona_box = gr.Textbox(label=tr["persona_label"], lines=3)

            with gr.Row():
                cond1_text = gr.Textbox(label=tr["cond1_text"], lines=4, elem_classes=["cond-response"])
                cond1_audio = gr.Audio(label=tr["cond1_audio"], type="filepath")
            cond1_chat = gr.Chatbot(label=tr["chat1"], height=240)
            with gr.Row():
                cond2_text = gr.Textbox(label=tr["cond2_text"], lines=4, elem_classes=["cond-response"])
                cond2_audio = gr.Audio(label=tr["cond2_audio"], type="filepath")
            cond2_chat = gr.Chatbot(label=tr["chat2"], height=240)

            gr.Markdown("### Debug: LLM Prompts (SYSTEM + USER)")
            cond1_prompt_box = gr.Textbox(label=tr["prompt1"], lines=6)
            cond2_prompt_box = gr.Textbox(label=tr["prompt2"], lines=6)

            state = gr.State({})

            run_button.click(
                lambda: gr.update(interactive=False),
                inputs=None,
                outputs=run_button,
                queue=False,
            ).then(
                handle_run,
                inputs=[
                    participant_id,
                    scenario_dropdown,
                    o,
                    c,
                    e_slider,
                    a_slider,
                    n_slider,
                    dbq_violations,
                    dbq_errors,
                    dbq_lapses,
                    bsss_experience,
                    bsss_thrill,
                    bsss_disinhibition,
                    bsss_boredom,
                    erq_reappraisal,
                    erq_suppression,
                    condition_order,
                    language,
                    endpoint_url,
                    model_name,
                    audio_in,
                    manual_text,
                    state,
                ],
                outputs=[
                    transcript_box,
                    persona_box,
                    cond1_text,
                    cond1_audio,
                    cond2_text,
                    cond2_audio,
                    cond1_prompt_box,
                    cond2_prompt_box,
                    cond1_chat,
                    cond2_chat,
                    state,
                ],
            ).then(
                lambda: gr.update(interactive=True),
                inputs=None,
                outputs=run_button,
                queue=False,
            )

            save1 = gr.Button(tr["save1"])
            save1_status = gr.Textbox(label=tr["save1_status"], interactive=False)
            save2 = gr.Button(tr["save2"])
            save2_status = gr.Textbox(label=tr["save2_status"], interactive=False)

            save1.click(
                lambda st: save_condition("condition1", st),
                inputs=[state],
                outputs=save1_status,
            )
            save2.click(
                lambda st: save_condition("condition2", st),
                inputs=[state],
                outputs=save2_status,
            )

            checkin_button.click(
                lambda: gr.update(interactive=False),
                inputs=None,
                outputs=checkin_button,
                queue=False,
            ).then(
                handle_checkin,
                inputs=[
                    participant_id,
                    scenario_dropdown,
                    o,
                    c,
                    e_slider,
                    a_slider,
                    n_slider,
                    dbq_violations,
                    dbq_errors,
                    dbq_lapses,
                    bsss_experience,
                    bsss_thrill,
                    bsss_disinhibition,
                    bsss_boredom,
                    erq_reappraisal,
                    erq_suppression,
                    language,
                    endpoint_url,
                    model_name,
                ],
                outputs=[checkin_status, checkin_audio, checkin_prompt_box],
            ).then(
                lambda: gr.update(interactive=True),
                inputs=None,
                outputs=checkin_button,
                queue=False,
            )

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

        def translate(lang: str, scenario_label_value: str):
            t = TRANSLATIONS.get(lang, TRANSLATIONS["en"])
            scenario_id = scenario_label_map.get(scenario_label_value, "")
            scen_text_val = get_scenario_text(scenario_id, lang) if scenario_id else ""
            return (
                gr.update(label=t["participant_id"]),
                gr.update(label=t["endpoint"]),
                gr.update(label=t["model"]),
                gr.update(label=t["lang_label"]),
                gr.update(label="LLM Status / Troubleshooting", value=t["llm_status_value"]),
                gr.update(label="Modell-Warmup (Whisper + TTS)", value=t["warmup_value"]),
                gr.update(label=t["scenario_label"]),
                gr.update(label=t["scenario_text_label"], value=scen_text_val),
                gr.update(label=t["condition_order_label"]),
                gr.update(label=t["big_five"][0]),
                gr.update(label=t["big_five"][1]),
                gr.update(label=t["big_five"][2]),
                gr.update(label=t["big_five"][3]),
                gr.update(label=t["big_five"][4]),
                gr.update(label=t["dbq"][0]),
                gr.update(label=t["dbq"][1]),
                gr.update(label=t["dbq"][2]),
                gr.update(label=t["bsss"][0]),
                gr.update(label=t["bsss"][1]),
                gr.update(label=t["bsss"][2]),
                gr.update(label=t["bsss"][3]),
                gr.update(label=t["erq"][0]),
                gr.update(label=t["erq"][1]),
                gr.update(label=t["audio_label"]),
                gr.update(label=t["text_input"], placeholder=t["text_placeholder"]),
                gr.update(value=t["run_button"]),
                gr.update(label=t["transcript_label"]),
                gr.update(label=t["persona_label"]),
                gr.update(label=t["cond1_text"]),
                gr.update(label=t["cond1_audio"]),
                gr.update(label=t["chat1"]),
                gr.update(label=t["cond2_text"]),
                gr.update(label=t["cond2_audio"]),
                gr.update(label=t["chat2"]),
                gr.update(label=t["prompt1"]),
                gr.update(label=t["prompt2"]),
                gr.update(value=t["checkin_button"]),
                gr.update(label=t["checkin_text"]),
                gr.update(label=t["checkin_audio"]),
                gr.update(label=t["checkin_prompt"]),
                gr.update(value=t["save1"]),
                gr.update(label=t["save1_status"]),
                gr.update(value=t["save2"]),
                gr.update(label=t["save2_status"]),
            )

        language.change(
            translate,
            inputs=[language, scenario_dropdown],
            outputs=[
                participant_id,
                endpoint_url,
                model_name,
                language,
                llm_status,
                warmup_status,
                scenario_dropdown,
                scenario_text,
                condition_order,
                o,
                c,
                e_slider,
                a_slider,
                n_slider,
                dbq_violations,
                dbq_errors,
                dbq_lapses,
                bsss_experience,
                bsss_thrill,
                bsss_disinhibition,
                bsss_boredom,
                erq_reappraisal,
                erq_suppression,
                audio_in,
                manual_text,
                run_button,
                transcript_box,
                persona_box,
                cond1_text,
                cond1_audio,
                cond1_chat,
                cond2_text,
                cond2_audio,
                cond2_chat,
                cond1_prompt_box,
                cond2_prompt_box,
                checkin_button,
                checkin_status,
                checkin_audio,
                checkin_prompt_box,
                save1,
                save1_status,
                save2,
                save2_status,
            ],
        )

    return demo


if __name__ == "__main__":
    interface = build_interface()
    interface.launch()
