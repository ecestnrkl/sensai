from typing import Tuple

from data import PERSONA_RULES, get_scenario_text


def build_persona_summary(
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
    response_lang: str,
) -> str:
    lang = "de" if response_lang == "de" else "en"
    de_rules = {
        "default": "Sprich mit dem Fahrer so wie es angemessen ist. Beruecksichtige seine Persoenlichkeitsmerkmale und Fahrweise.",
        "high_neuroticism": "Fahrer wirkt aengstlich; mehr Bestaetigung, langsames Tempo, Stress anerkennen.",
        "high_extraversion": "Fahrer ist gesellig; Ton warm und kurz ermutigend halten.",
        "high_agreeableness": "Fahrer mag Zusammenarbeit; inklusive, sanfte Formulierungen nutzen.",
        "low_agreeableness": "Fahrer koennte widersprechen; direkt, faktenbasiert, Nutzen betonen.",
        "dbq_violations_high": "Neigt zu Regelverstoessen; Sicherheit, Legalitaet und Folgen klar hervorheben.",
        "dbq_errors_high": "Fehleranfaellig; Schritt-fuer-Schritt, eindeutig, ggf. Bestaetigung einholen.",
        "dbq_lapses_high": "Unaufmerksamkeiten moeglich; simpel halten, Kernpunkte kurz wiederholen.",
        "bsss_experience_high": "Sucht neue Erfahrungen; Vorschlaege sicher rahmen.",
        "bsss_thrill_high": "Mag Thrill; Risiko herunterspielen, sichere Alternativen anbieten.",
        "bsss_disinhibition_high": "Impulsiv; Zurueckhaltung, ruhiger Ton, sofort sichere Schritte betonen.",
        "bsss_boredom_high": "Wird schnell gelangweilt; kurzweilig, aber sicher bleiben (Musik/Podcast).",
    }
    rules = de_rules if lang == "de" else PERSONA_RULES
    summary_parts = [rules.get("default", "")]
    if n >= 4:
        summary_parts.append(rules.get("high_neuroticism", ""))
    if e >= 4:
        summary_parts.append(rules.get("high_extraversion", ""))
    if a >= 4:
        summary_parts.append(rules.get("high_agreeableness", ""))
    if a <= 2:
        summary_parts.append(rules.get("low_agreeableness", ""))
    if dbq_violations >= 4:
        summary_parts.append(rules.get("dbq_violations_high", ""))
    if dbq_errors >= 4:
        summary_parts.append(rules.get("dbq_errors_high", ""))
    if dbq_lapses >= 4:
        summary_parts.append(rules.get("dbq_lapses_high", ""))
    if bsss_experience >= 4:
        summary_parts.append(rules.get("bsss_experience_high", ""))
    if bsss_thrill >= 4:
        summary_parts.append(rules.get("bsss_thrill_high", ""))
    if bsss_disinhibition >= 4:
        summary_parts.append(rules.get("bsss_disinhibition_high", ""))
    if bsss_boredom >= 4:
        summary_parts.append(rules.get("bsss_boredom_high", ""))
    if lang == "de":
        summary_parts.append(
            f"Big Five (1-5): O={o}, C={c}, E={e}, A={a}, N={n}. "
            f"Mini-DBQ (1-5): Verstoesse={dbq_violations}, Fehler={dbq_errors}, Unaufmerksamkeiten={dbq_lapses}. "
            f"BSSS (1-7): Erfahrung={bsss_experience}, Thrill={bsss_thrill}, Enthemmung={bsss_disinhibition}, Langeweile={bsss_boredom}."
        )
    else:
        summary_parts.append(
            f"Big Five (1-5): O={o}, C={c}, E={e}, A={a}, N={n}. "
            f"Mini-DBQ (1-5): violations={dbq_violations}, errors={dbq_errors}, lapses={dbq_lapses}. "
            f"BSSS (1-7): experience={bsss_experience}, thrill={bsss_thrill}, disinhibition={bsss_disinhibition}, boredom={bsss_boredom}."
        )
    return " ".join([p.strip() for p in summary_parts if p]).strip()


def base_system_prompt(scenario_id: str, response_lang: str) -> str:
    scenario_text = get_scenario_text(scenario_id, response_lang)
    if response_lang == "de":
        return (
            "Du bist ein Sprach-Assistent im Fahrzeug. Antworte ausschließlich knapp auf Deutsch, maximal drei kurze Sätze. "
            "Verwende keine englischen Wörter oder Halbsätze; falls du Englisch nutzt, wiederhole sofort nur auf Deutsch. "
            "Keine Meta-Einleitungen wie 'Hier ist meine Antwort'; antworte direkt, klar und grammatikalisch sauber. "
            f"Szenario: {scenario_text}"
        )
    return (
        f"You are a voice assistant in a vehicle. Answer only shortly in English, maximum three short sentences. "
        "Do not use any German words; if you do, restate in English only. "
        "No meta openers like 'Here is my answer'; answer directly, clearly, with proper grammar. "
        f"Scenario context: {scenario_text}"
    )


def user_prompt(transcript: str, response_lang: str) -> str:
    if response_lang == "de":
        return (
            f"Fahrer-Transkript (Sprache=de): {transcript}. "
            "Antworte strikt auf Deutsch; keine englischen Wörter oder Mischungen. "
            "Keine Meta-Sätze (z.B. 'hier ist meine Antwort'). Gib klare, grammatikalisch korrekte Sätze."
        )
    return (
        f"Driver transcript (lang={response_lang}): {transcript}. "
        "Answer strictly in English; do not mix languages. "
        "Avoid meta phrases (e.g., 'here is my answer'). Provide clear, grammatically correct sentences."
    )


def checkin_prompts(
    scenario_id: str, response_lang: str, persona_summary: str
) -> Tuple[str, str]:
    scenario_text = get_scenario_text(scenario_id, response_lang)
    if response_lang == "de":
        system_prompt = (
            "Du bist ein Sprach-Assistent im Fahrzeug. Antworte ausschließlich auf Deutsch, maximal zwei kurze Sätze. "
            "Verwende keine englischen Wörter oder Halbsätze. "
            f"Szenario: {scenario_text}. Persona hints: {persona_summary}"
        )
        user_prompt = (
            "Beginne mit einer kurzen, empathischen Check-in-Frage wie 'Wie geht es Ihnen?'. "
            "Bleibe ausschließlich auf Deutsch; keine englischen Wörter. Kontext nur kurz erwähnen."
        )
    else:
        system_prompt = (
            "You are a voice assistant in a vehicle. Answer only in English, max two short sentences. "
            "Do not use any German words. "
            f"Scenario: {scenario_text}. Persona hints: {persona_summary}"
        )
        user_prompt = (
            "Start with a brief empathetic check-in like 'How are you doing?'. "
            "Stay strictly in English; no German words. Mention driving context only briefly."
        )
    return system_prompt, user_prompt
