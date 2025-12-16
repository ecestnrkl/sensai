import re
from typing import Tuple

from data import PERSONA_RULES, get_scenario_text


def format_driver_scenario(text: str) -> str:
    """Rewrite scenario text to third person and clean punctuation."""
    if not text:
        return ""
    t = text.strip()

    # Drop "Imagine..." / "Stell dir vor..." intros so the scenario reads as direct context.
    t = re.sub(r"^(stell dir vor)(,)?\s+", "", t, flags=re.IGNORECASE)
    t = re.sub(r"^(imagine)( that)?(,)?\s+", "", t, flags=re.IGNORECASE)

    # German: map 2nd-person ("du/dein") to driver context.
    if re.search(r"\bdu\b|\bdein", t, flags=re.IGNORECASE):
        t = re.sub(r"\bfühlst\s+dich\b", "fühlt sich", t, flags=re.IGNORECASE)
        replacements = [
            (r"\bdeinen\b", "seinen"),
            (r"\bdeinem\b", "seinem"),
            (r"\bdeiner\b", "seiner"),
            (r"\bdeine\b", "seine"),
            (r"\bdein\b", "sein"),
            (r"\bdu\b", "der Fahrer"),
            (r"\bbist\b", "ist"),
            (r"\bhast\b", "hat"),
            (r"\bfährst\b", "fährt"),
            (r"\bsteckst\b", "steckt"),
            (r"\bfühlst\b", "fühlt"),
            (r"\bkommst\b", "kommt"),
            (r"\bweißt\b", "weiß"),
            (r"\bwirst\b", "wird"),
        ]
        for pattern, replacement in replacements:
            t = re.sub(pattern, replacement, t, flags=re.IGNORECASE)
        t = re.sub(r"(^|[.!?]\s+)der Fahrer\b", r"\1Der Fahrer", t)

    # English: map 2nd-person ("you/your") to driver context.
    elif re.search(r"\byou\b|\byour\b|\byou['’](re|ll|ve|d)\b", t, flags=re.IGNORECASE):
        t = re.sub(
            r"(^|[.!?]\s+)you\s+know\b", r"\1The driver knows", t, flags=re.IGNORECASE
        )
        t = re.sub(
            r"(^|[.!?]\s+)you\s+are\b", r"\1The driver is", t, flags=re.IGNORECASE
        )
        t = re.sub(
            r"(^|[.!?]\s+)you['’]re\b", r"\1The driver is", t, flags=re.IGNORECASE
        )
        t = re.sub(r"\byou['’]re\b", "they are", t, flags=re.IGNORECASE)
        t = re.sub(r"\byou['’]ll\b", "they will", t, flags=re.IGNORECASE)
        t = re.sub(r"\byou['’]ve\b", "they have", t, flags=re.IGNORECASE)
        t = re.sub(r"\byou['’]d\b", "they would", t, flags=re.IGNORECASE)
        t = re.sub(r"\byour\b", "their", t, flags=re.IGNORECASE)
        t = re.sub(r"\byou\b", "they", t, flags=re.IGNORECASE)

    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"\.{2,}", ".", t)
    t = t.rstrip(" .")
    if t and not t.endswith("."):
        t = f"{t}."
    return t


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
    scenario_text = format_driver_scenario(get_scenario_text(scenario_id, response_lang))
    if response_lang == "de":
        return (
            "Du bist ein Sprach-Assistent im Fahrzeug. Antworte ausschließlich knapp auf Deutsch, genau zwei kurze Sätze. "
            "Verwende keine englischen Wörter oder Halbsätze; falls du Englisch nutzt, wiederhole sofort nur auf Deutsch. "
            "Klingt wie gesprochene Sprache: locker, freundlich, aber klar. "
            "Keine Meta-Einleitungen oder Füllwörter ('natürlich', 'okay', 'hier ist'), keine Listen/Nummerierungen. "
            "Antworte direkt, klar und grammatikalisch sauber. "
            "Das Szenario beschreibt die Situation des Fahrers (nicht deine eigene). "
            f"Szenario: {scenario_text}"
        )
    return (
        f"You are a voice assistant in a vehicle. Answer only in English, exactly two short sentences. "
        "Do not use any German words; if you do, restate in English only. "
        "Sound like natural spoken language: friendly, concise, no lists/numbering. "
        "No meta openers or fillers (e.g., 'Of course', 'Sure', 'Here are'). "
        "Answer directly, clearly, with proper grammar. "
        "The scenario describes the driver's situation (not yours). "
        f"Scenario context: {scenario_text}"
    )


def user_prompt(transcript: str, response_lang: str) -> str:
    if response_lang == "de":
        return (
            f"Fahrer-Transkript (Sprache=de): {transcript}. "
            "Antworte strikt auf Deutsch; keine englischen Wörter oder Mischungen. "
            "Keine Meta-Sätze oder Füllwörter (z.B. 'natürlich', 'gerne'), keine Listen/Nummerierungen. "
            "Klingt wie gesprochene Sprache, genau zwei klare Sätze."
        )
    return (
        f"Driver transcript (lang={response_lang}): {transcript}. "
        "Answer strictly in English; do not mix languages. "
        "Avoid meta phrases or fillers (e.g., 'of course', 'sure', 'here are'), and do not use lists/numbering. "
        "Sound like natural spoken English, exactly two clear sentences."
    )


def checkin_prompts(
    scenario_id: str, response_lang: str, persona_summary: str
) -> Tuple[str, str]:
    scenario_text = format_driver_scenario(get_scenario_text(scenario_id, response_lang))
    if response_lang == "de":
        system_prompt = (
            "Du bist ein Sprach-Assistent im Fahrzeug. Antworte ausschließlich auf Deutsch, genau zwei kurze, vollständige Sätze (<30 Wörter). "
            "Keine englischen Wörter oder Halbsätze. Keine Füllwörter oder Ich-Aussagen über dein Befinden. Ruhiger Navi-Ton. "
            "Das Szenario beschreibt die Situation des Fahrers (nicht deine eigene). "
            f"Szenario: {scenario_text}. Persona hints: {persona_summary}"
        )
        user_prompt = (
            "Stelle dem Fahrer eine kurze, ruhige Frage wie 'Wie geht es Ihnen gerade?'. "
            "Keine englischen Wörter. Keine Ich-Aussagen über Stimmung ('mir geht es', 'ich fühle', 'ich bin'). "
            "Keine Listen, keine Wiederholung des Prompts oder der Eingabe."
        )
    else:
        system_prompt = (
            "You are a voice assistant in a vehicle. Answer only in English, exactly two short, complete sentences (<30 words). "
            "No German words or code-switching. No meta phrases or filler. Calm navigation tone. "
            "The scenario describes the driver's situation (not yours). "
            f"Scenario: {scenario_text}. Persona hints: {persona_summary}"
        )
        user_prompt = (
            "Ask the driver a short, calm check-in question like 'How are you doing right now?'. "
            "No German words. No self-talk about your own feelings. No lists; do not echo the prompt or input."
        )
    return system_prompt, user_prompt
