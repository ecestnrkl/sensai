# Promptflow: SensAI Experiment Pipeline

This document visualises the full data flow from user input to LLM response,
including the **DPP branch** (Driver Personality Profile = Big Five + DBQ + BSSS + ERQ).

**Status:** All four original bottlenecks have been fixed. See section 2 for details.

---

## 1. Full Promptflow

```mermaid
flowchart TD
    %% ── Inputs ──────────────────────────────────────────────────
    A1([Participant ID\nScenario · Language · Run-Mode])
    A2([Big Five\nO · C · E · A · N\nScale 1–5])
    A3([Mini-DBQ\nViolations · Errors · Lapses\nScale 1–5])
    A4([BSSS\nExperience · Thrill · Disinhibition · Boredom\nScale 1–5])
    A5([ERQ\nReappraisal · Suppression\nScale 1–7])
    A6([Audio Recording\nor\nManual Text])

    %% ── Transcription ───────────────────────────────────────────
    B1["_get_transcript()\nWhisper 'base' model\nor manual text"]

    %% ── DPP → Persona Summary ──────────────────────────────────
    C1{{"✅ FIXED 1\nbuild_persona_summary()\nprompts.py\n\n3-tier rules for ALL traits:\nscore ≥ 4 → high rule\nscore = 3 → mid rule\nscore ≤ 2 → low rule\nO, C, ERQ now included"}}
    C2["Persona Summary String\n(every trait produces a rule)"]

    %% ── System Prompt ───────────────────────────────────────────
    D1["base_system_prompt()\nprompts.py\n\nFixed content (always identical):\n• Role: voice assistant in vehicle\n• Format: 2–4 short sentences\n• Language purity\n• No fillers / no lists\n• Scenario context"]

    %% ── Condition Branch ────────────────────────────────────────
    D2{{"✅ FIXED 2\ncondition == 'personalized'?\n_generate_llm_response()\nhandlers.py"}};

    D3["system_prompt =\n'Driver personality profile:\n{persona_summary}'\n\n+ base_system\n\n→ Persona profile placed FIRST\nfor maximum LLM attention weight"]
    D4["system_prompt =\nbase_system\n(no persona profile)"]
    D5["user_prompt()\nprompts.py\n\n'Driver transcript (lang=...): {...}.\nAnswer in 2–4 clear sentences.'"]

    %% ── Message List → LLM ──────────────────────────────────────
    E1{{"✅ FIXED 3\ncall_llm()\nllm_client.py\n\nMessage list:\n1. system (with/without profile)\n2. chat_history (prior turns)\n3. user_prompt\n\nParameters:\ntemperature=0.8  ← raised\nmax_tokens=140   ← expanded\ntop_p=0.9"}}
    E2["LLM\n(Ollama / OpenAI-compatible)\nRaw Response"]

    %% ── Post-Processing ─────────────────────────────────────────
    F1["sanitize_llm_output()\nllm_client.py\nRemoves: *bold*, [text],\nmeta-openers like 'Sure:', 'Klar:',\ntranscript echoes"]
    F2["filter_by_language()\nllm_client.py\nRemoves cross-language words"]
    F3{"looks_wrong_language()?"}
    F4["rewrite_for_language()\nsecond LLM call\nlanguage correction only"]
    F5{{"✅ FIXED 4\ntruncate_response()\nllm_client.py\n\nMax: 4 sentences / 55 words / 450 chars\n→ room for tone and style variation"}}

    %% ── Output ──────────────────────────────────────────────────
    G1["Final LLM Response\n(Text)"]
    G2["TTS: synthesize_speech()\naudio_io.py\nXTTS v2 → .wav"]
    G3["CSV Log\nresults.csv\n(both conditions)"]

    %% ── Connections ─────────────────────────────────────────────
    A1 --> B1
    A6 --> B1
    A2 & A3 & A4 & A5 --> C1
    B1 --> D5
    C1 --> C2
    C2 --> D2
    D1 --> D2
    D2 -- "yes" --> D3
    D2 -- "no" --> D4
    D3 & D4 --> E1
    D5 --> E1
    E1 --> E2
    E2 --> F1
    F1 --> F2
    F2 --> F3
    F3 -- "yes" --> F4
    F3 -- "no" --> F5
    F4 --> F5
    F5 --> G1
    G1 --> G2
    G1 --> G3

    %% ── Styling ─────────────────────────────────────────────────
    classDef fixed fill:#00b894,color:#fff,stroke:#00856f,stroke-width:2px
    classDef input fill:#74b9ff,color:#000,stroke:#0984e3,stroke-width:1px
    classDef process fill:#dfe6e9,color:#000,stroke:#636e72,stroke-width:1px
    classDef output fill:#55efc4,color:#000,stroke:#00b894,stroke-width:1px

    class C1,D2,E1,F5 fixed
    class A1,A2,A3,A4,A5,A6 input
    class B1,C2,D1,D3,D4,D5,F1,F2,F4 process
    class G1,G2,G3 output
```

---

## 2. Die 4 Problemstellen — Warum DPP keinen Unterschied macht

| # | Wo im Code | Problem | Datei / Funktion |
|---|-----------|---------|-----------------|
| **1** | `build_persona_summary()` | Schwellenwert ist `≥ 4` (bzw. `≤ 2`). Bei **mittleren Scores** (2–3) wird **keine Persona-Regel** hinzugefügt — nur der `default`-Text. D.h. die meisten realen Teilnehmer bekommen identische Persona-Hints. | [prompts.py](prompts.py) |
| **2** | `_generate_llm_response()` | `Persona hints: ...` wird ans **Ende** des System Prompts angehängt, **nach** den harten Format-Constraints (`"exactly two short sentences"`). LLMs gewichten frühere Tokens stärker → Format-Regeln überschreiben Persona-Anpassungen. | [handlers.py](handlers.py) |
| **3** | `call_llm()` | `temperature=0.6` (Settings) erzeugt **deterministischere Outputs**. Bei niedriger Temperatur tendiert das Modell zur wahrscheinlichsten Antwort — unabhängig von Persona-Hints. Außerdem: `max_tokens=90` → sehr wenig Raum für Stil-Variation. | [llm_client.py](llm_client.py) / [settings.py](settings.py) |
| **4** | `truncate_response()` | Schneidet auf max. **2 Sätze / 30 Wörter / 280 Zeichen**. Selbst wenn das LLM personalisiert antwortet, werden Ton- und Stil-Unterschiede durch diesen Schritt **homogenisiert**. Auch `sanitize_llm_output()` filtert Formulierungen heraus, die Persona-typisch sein könnten. | [llm_client.py](llm_client.py) |

---

## 3. Comparison Table: Personalized vs. Non-Personalized (After Fixes)

| Step | Non-Personalized | Personalized | Difference measurable? |
|------|-----------------|--------------|------------------------|
| `base_system_prompt()` | identical | identical | ❌ No |
| DPP profile block | not present | `"Driver personality profile:\n{summary}"` prepended | ✅ **Yes — at the top** |
| `user_prompt()` | identical | identical | ❌ No |
| `chat_history` | separate stack per condition | separate stack per condition | ❌ No (both start empty) |
| `temperature=0.8` | identical | identical | ✅ Higher variability → profile has more impact |
| `max_tokens=140` | identical | identical | ✅ Enough room for 2–4 varied sentences |
| `sanitize_llm_output()` | applied identically | applied identically | Neutral |
| `truncate_response()` | max 4 sentences / 55 words | max 4 sentences / 55 words | ✅ No longer clips persona-driven style |
| **Final response** | — | — | **Should differ noticeably in tone, phrasing and emphasis** |

---

## 4. Personality → Response Behaviour Reference

How each DPP trait should now shape the LLM response:

| Trait | Low (≤2) | Mid (3) | High (≥4, ERQ ≥5) |
|-------|----------|---------|-------------------|
| **O** Openness | Familiar, conventional advice only | One practical option mentioned | Offer alternative framing or creative reframe |
| **C** Conscientiousness | Single immediate step, no multi-part | One clear action | Precise, structured, acknowledge planning |
| **E** Extraversion | Minimal, calm, non-intrusive | Friendly but brief | Warm, conversational, brief encouragement |
| **A** Agreeableness | Direct, factual, emphasize benefit | Neutral helpful | Inclusive, gentle, "we"-framing |
| **N** Neuroticism | Skip reassurance, direct advice | One brief reassuring phrase first | Acknowledge stress first, heavy reassurance |
| **DBQ Violations** | No safety emphasis | Brief safety reminder | Explicit legal/safety warning |
| **DBQ Errors** | Standard | Clear simple instruction | Step-by-step, unambiguous |
| **DBQ Lapses** | Standard | Single focus point | Very simple, possible key-point repeat |
| **BSSS Experience** | Conventional | One option mentioned | Frame as enriching, safe option |
| **BSSS Thrill** | Affirm caution | Gentle caution, acknowledge feeling | Redirect to safe alternative |
| **BSSS Disinhibition** | Standard | Brief grounding phrase | Stress restraint + immediate safe step |
| **BSSS Boredom** | Standard | Acknowledge monotony, light distraction | Engaging tone + suggest music/podcast |
| **ERQ Reappraisal** | Direct practical help only | Gentle reframe offered | Actively suggest positive reinterpretation |
| **ERQ Suppression** | Standard | Light acknowledgment before advice | Acknowledge emotional state first, then advise |

---

## 5. Validation Snippet

Run this in the project directory to check the persona summary is now non-trivial for mid-range scores:

```python
import sys; sys.path.insert(0, '.')
from prompts import build_persona_summary

# All mid-range — should now produce rules for every trait:
summary = build_persona_summary(3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 4, 3, "en")
print(summary)

# High N, low C — should produce heavy reassurance + single-step instruction:
summary2 = build_persona_summary(3, 1, 3, 3, 5, 2, 3, 3, 3, 3, 3, 3, 3, 3, "en")
print(summary2)
```
