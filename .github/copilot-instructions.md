# Copilot Instructions: Audio Personality Prompting Prototype

## Project Overview
A Gradio-based research app for comparing personalized vs. non-personalized LLM responses in driving scenarios. Uses speech-to-text (Whisper), LLM generation, and text-to-speech (Coqui XTTS v2) to simulate an in-vehicle voice assistant. Supports bilingual operation (English/German).

## Architecture & Data Flow

### Core Pipeline (handlers.py → llm_client.py → audio_io.py)
1. **Input**: Audio (mic) or text → Whisper transcription (`transcribe_audio`)
2. **Prompt Construction**: Build persona-aware or baseline prompts using Big Five + DBQ + BSSS + ERQ scores
3. **LLM Generation**: Parallel execution of 1-2 conditions (personalized/non-personalized) with conversation history
4. **Post-processing**: Language filtering, sanitization, truncation (2 sentences max)
5. **TTS**: Coqui XTTS v2 synthesis with speaker selection
6. **CSV Logging**: Save run metadata + responses to `results.csv`

### Key Components
- **app.py**: Gradio UI with bilingual translations (`TRANSLATIONS` dict), CSS styling for condition highlighting
- **handlers.py**: Core orchestration (`handle_run`, `handle_checkin`, `save_condition`)
- **prompts.py**: Prompt templates + persona rule application. Critical: `format_driver_scenario()` rewrites 2nd-person scenarios to 3rd-person for LLM context
- **llm_client.py**: OpenAI/Ollama API client with auto-detection (`detect_api_style`), language leak scrubbing
- **audio_io.py**: Lazy-loaded Whisper/TTS models (`get_whisper()`, `get_tts()`), temp audio in `tmp_audio/`
- **data.py**: JSON loaders for `scenarios.json` (driving scenarios) and `persona_rules.json` (personality → instruction mappings)

## Critical Conventions

### Bilingual String Handling
- All user-facing strings live in `TRANSLATIONS` dict (app.py). Add new UI labels to BOTH `"en"` and `"de"` keys
- LLM prompts enforce strict language purity: "No English words in German responses" and vice versa
- `response_lang` defaults to detected Whisper language, fallback to UI toggle
- Use `filter_by_language()` and `scrub_language_leaks()` in llm_client.py for post-processing

### Persona System (prompts.py)
- Persona rules from `persona_rules.json` are threshold-based (e.g., `n >= 4` → high neuroticism)
- `build_persona_summary()` concatenates applicable rules + numeric scores
- Personalized condition: append `"Persona hints: {summary}"` to system prompt
- Non-personalized: use only `base_system_prompt()` without persona

### LLM Response Constraints
- **Always 2 sentences**: Enforced via prompts + `truncate_response()` in llm_client.py
- **No formatting**: Strip markdown asterisks, brackets, numbering via `sanitize_llm_output()`
- **No meta-language**: Remove "Here's my answer", "okay", "sure" patterns (regex in sanitize function)
- **Conversational tone**: "Sound like natural spoken language" in system prompts

### Scenario Format Transformation
- Scenarios stored as 2nd-person ("you are driving...") in `scenarios.json`
- `format_driver_scenario()` converts to 3rd-person ("the driver is...") for LLM context
- Handles German (`du → der Fahrer`) and English (`you → they`) transformations
- Rationale: LLM plays assistant role, not the driver

### API Compatibility (llm_client.py)
- Auto-detect Ollama (port 11434, `/api/chat`) vs. OpenAI (`/v1/chat/completions`)
- Ollama uses `options.num_predict`, OpenAI uses `max_tokens`
- `normalized_url()` appends correct endpoint paths if missing

## Development Workflows

### Setup & Dependencies
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install --upgrade "transformers<4.46" torch==2.5.1 torchaudio==2.5.1
pip install gradio faster-whisper soundfile numpy requests TTS
```
**Critical version pins**: transformers <4.46 (BeamSearchScorer issue), torch 2.5.1 (weights_only compatibility)

### Running the App
```bash
python app.py  # Launch Gradio on http://127.0.0.1:7860
```
First run: Expect 1-2 min model downloads (Whisper base, XTTS v2). Use "Warmup" button to preload.

### LLM Server (Default: Ollama)
```bash
ollama serve
ollama pull llama2:7b-chat  # Must match DEFAULT_MODEL in settings.py
```
Alternative: llama.cpp server must use `--chat_format llama-2` and matching endpoint/model in UI.

### Testing Changes
1. **LLM Connection**: Use "Test LLM Connection" button (calls `test_llm_connection()`)
2. **Transcription**: Check `transcript_box` output after mic/text input
3. **Persona Logic**: Inspect `persona_box` and debug prompt boxes (SYSTEM + USER)
4. **TTS**: Verify audio playback; check `tmp_audio/` for generated files
5. **CSV Logging**: Confirm `results.csv` updates after "Save Condition" clicks

## Configuration Files

### scenarios.json
```json
[
  {"id": "unique_id", "title": "Display Name", "text": "English 2nd-person scenario", "text_de": "German scenario"}
]
```
Add new scenarios here. UI dropdown populates from `title (id)`.

### persona_rules.json
```json
{
  "high_neuroticism": "Instruction text for anxious drivers",
  "dbq_violations_high": "Safety emphasis for rule breakers"
}
```
Keys map to threshold checks in `build_persona_summary()`. Add new traits by:
1. Define rule in JSON
2. Add threshold logic in `build_persona_summary()`

### settings.py
- `DEFAULT_ENDPOINT`, `DEFAULT_MODEL`: Pre-fill LLM connection fields
- `MAX_GENERATION_TOKENS`: LLM output limit (default 90)
- `DEFAULT_TEMPERATURE`, `DEFAULT_TOP_P`: LLM sampling params
- Environment vars: `TTS_SPEAKER_NAME`, `TTS_SPEAKER_WAV` for custom voice

## Common Tasks

### Adding a New Personality Scale
1. Add slider in app.py "Experiment" tab
2. Update `build_persona_summary()` in prompts.py with threshold logic
3. Add rule text to `persona_rules.json`
4. Add column to `results.csv` header in `ensure_results_file()`
5. Update `append_result_row()` to save new value

### Changing Response Length
Modify `truncate_response()` in llm_client.py. Current: 2 sentences via regex `r'([^.!?]*[.!?]){1,2}'`

### Debugging Language Leaks
Check `scrub_language_leaks()` patterns in llm_client.py. Add common code-switching words to `leaks_de` or `leaks_en` lists.

### Custom TTS Voice
Set environment variable: `export TTS_SPEAKER_WAV=/path/to/voice.wav` before running app.

## Anti-Patterns to Avoid
- **Don't** use UI language (`language` radio) for LLM prompts; always use detected `response_lang`
- **Don't** modify scenario text at runtime; transformations go through `format_driver_scenario()`
- **Don't** call LLM without conversation history for multi-turn interactions (breaks context)
- **Don't** forget to update both conditions of TRANSLATIONS when adding UI strings
