# Promptflow: SensAI Experiment Pipeline

This document visualises the full data flow from user input to LLM response,
including the **DPP branch** (Driver Personality Profile = Big Five + DBQ + BSSS + ERQ)
and an analysis of why the DPP currently has little or no measurable effect on the LLM output.

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
    C1{{"⚠️ PROBLEM 1\nbuild_persona_summary()\nprompts.py\n\nThreshold logic:\nRule added ONLY if\nscore ≥ 4 (or ≤ 2)\n→ mid-range scores\n= default rule only!"}}
    C2["Persona Summary String\ne.g. 'Speak calmly. Driver seems anxious;\nmore reassurance... Big Five: O=3, C=4...'"]

    %% ── System Prompt ───────────────────────────────────────────
    D1["base_system_prompt()\nprompts.py\n\nFixed content (always identical):\n• Role: voice assistant in vehicle\n• Format: exactly 2 short sentences\n• Language purity\n• No fillers / no lists\n• Scenario context"]

    %% ── Condition Branch ────────────────────────────────────────
    D2{{"⚠️ PROBLEM 2\ncondition == 'personalized'?\n_generate_llm_response()\nhandlers.py"}};

    D3["system_prompt =\nbase_system\n+ ' Persona hints: '\n+ persona_summary\n\n→ Persona hints placed AT THE END\nof the prompt, AFTER the hard\nformat constraints"]
    D4["system_prompt =\nbase_system\n(no persona hints)"]
    D5["user_prompt()\nprompts.py\n\n'Driver transcript (lang=...): {...}.\nAnswer strictly in English,\nexactly two clear sentences.'"]

    %% ── Message List → LLM ──────────────────────────────────────
    E1{{"⚠️ PROBLEM 3\ncall_llm()\nllm_client.py\n\nMessage list:\n1. system (with/without hints)\n2. chat_history (prior turns)\n3. user_prompt\n\nParameters:\ntemperature=0.6  ← low!\nmax_tokens=90    ← tight!\ntop_p=0.9"}}
    E2["LLM\n(Ollama / OpenAI-compatible)\nRaw Response"]

    %% ── Post-Processing ─────────────────────────────────────────
    F1{{"⚠️ PROBLEM 4a\nsanitize_llm_output()\nllm_client.py\n\nRemoves: *bold*, [text],\nmeta-openers like 'Sure:', 'Klar:'\ntranscript echoes\n→ may remove persona-typical\nformulations"}}
    F2["filter_by_language()\nllm_client.py\nRemoves cross-language words"]
    F3{"looks_wrong_language()?"}
    F4["rewrite_for_language()\nsecond LLM call\nlanguage correction only"]
    F5{{"⚠️ PROBLEM 4b\ntruncate_response()\nllm_client.py\n\nMax: 2 sentences / 30 words / 280 chars\n→ tone and style differences\n(produced by DPP) are\ncut off here!"}}

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
    classDef problem fill:#ff6b6b,color:#fff,stroke:#c0392b,stroke-width:2px
    classDef input fill:#74b9ff,color:#000,stroke:#0984e3,stroke-width:1px
    classDef process fill:#dfe6e9,color:#000,stroke:#636e72,stroke-width:1px
    classDef output fill:#55efc4,color:#000,stroke:#00b894,stroke-width:1px

    class C1,D2,E1,F1,F5 problem
    class A1,A2,A3,A4,A5,A6 input
    class B1,C2,D1,D3,D4,D5,F2,F4 process
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

## 3. Comparison Table: Personalized vs. Non-Personalized

| Step | Non-Personalized | Personalized | Difference measurable? |
|------|-----------------|--------------|------------------------|
| `base_system_prompt()` | identical | identical | ❌ No |
| `+ Persona hints:` | not present | `persona_summary` string appended | ✅ Yes, in the prompt |
| `user_prompt()` | identical | identical | ❌ No |
| `chat_history` | separate stack per condition | separate stack per condition | ❌ No (both start empty) |
| `temperature=0.6` | identical | identical | ❌ Determinism suppresses differences |
| `max_tokens=90` | identical | identical | ❌ Little room for variation |
| `sanitize_llm_output()` | applied identically | applied identically | ❌ May strip persona-style phrasing |
| `truncate_response()` | max 2 sentences / 30 words | max 2 sentences / 30 words | ❌ **Eliminates remaining differences** |
| **Final response** | — | — | **Very similar or identical** |

---

## 4. Debug Suggestions: Making Pipeline Differences Visible

### 4.1 Log the prompt diff directly (partially already in place)

`_generate_llm_response()` in [handlers.py](handlers.py) already returns a `prompt_debug` string.
The UI displays it as "Debug-Prompt". Check there whether the system prompts for both conditions
actually differ:

```
# Personalized system prompt (Auszug):
"...Answer directly, clearly, with proper grammar. Scenario context: [...] 
Persona hints: Speak calmly. Driver seems anxious; more reassurance needed. Big Five: O=3, C=4..."

# Non-Personalized system prompt (Auszug):
"...Answer directly, clearly, with proper grammar. Scenario context: [...]"
```

→ If the strings differ, the problem lies **in the LLM or the post-processing**, not in the prompt construction.

---

### 4.2 Raise temperature for testing

In [settings.py](settings.py), temporarily:

```python
# Before:
DEFAULT_TEMPERATURE = 0.6

# For testing:
DEFAULT_TEMPERATURE = 1.2   # higher variability → persona influence becomes visible
```

> **Warning:** For debug purposes only. At `temperature > 1.0` responses become less coherent.

---

### 4.3 Disable truncate_response()

In [handlers.py](handlers.py) inside `_generate_llm_response()`:

```python
# Before:
cleaned_response = truncate_response(cleaned_response, response_lang)

# Comment out for testing:
# cleaned_response = truncate_response(cleaned_response, response_lang)
```

→ Reveals whether the LLM actually produces **longer / differently-toned** responses for `personalized`
before they are cut off.

---

### 4.4 Print persona summary for all score ranges

In [prompts.py](prompts.py) — `build_persona_summary()` — test whether the threshold actually fires:

```python
# Debug: what is generated for typical mid-range values (all = 3)?
from prompts import build_persona_summary
summary = build_persona_summary(3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 4, 3, "de")
print(repr(summary))
# Expected result: only default rule + numbers → no persona-specific content!
```

---

### 4.5 Move persona hints to the beginning of the system prompt

In [handlers.py](handlers.py) inside `_generate_llm_response()`:

```python
# Current (hints at the end):
system_prompt = f"{base_system} Persona hints: {persona_summary}"

# Experiment (hints at the start — weighted more heavily by the LLM):
system_prompt = f"Persona hints: {persona_summary}\n\n{base_system}"
```

→ Tests whether the **position of the hints** in the prompt produces a measurable difference.
