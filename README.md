# Audio Personality Prompting Prototype
Gradio app to compare LLM replies with and without persona hints. Audio input (mic), Whisper transcription, Coqui XTTS v2 TTS. UI default is English; German via toggle. Below: full English guide + German short version.

## English Guide
### Requirements
- Python 3.11, Git, microphone.
- LLM server: easiest Ollama (chat endpoint) or any OpenAI-compatible chat server (e.g., llama.cpp server).
- Network access for model downloads (Whisper, XTTS, Ollama pulls).

### Setup (macOS/Linux, Bash)
```bash
git clone <repo> prototype_audio_test
cd prototype_audio_test
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install --upgrade "transformers<4.46" torch==2.5.1 torchaudio==2.5.1 TTS==0.22.0
pip install gradio faster-whisper soundfile numpy requests TTS
```

### Setup (Windows, PowerShell)
```powershell
git clone <repo> prototype_audio_test
cd prototype_audio_test
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install --upgrade "transformers<4.46" torch==2.5.1 torchaudio==2.5.1 TTS==0.22.0
pip install gradio faster-whisper soundfile numpy requests TTS
```
Note: Ollama officially supports macOS/Linux; on Windows use WSL or another OpenAI-compatible endpoint.

### Start LLM server
**Option A: Ollama (recommended)**
```bash
ollama serve           # keep terminal open
ollama pull llama2:7b-chat
```
UI defaults match: Endpoint `http://localhost:11434`, Model `llama2:7b-chat`.

**Option B: llama.cpp server (CPU example)**
```bash
python -m venv ~/.llama-venv && source ~/.llama-venv/bin/activate
python -m pip install --upgrade pip
pip install llama-cpp-python
python -m llama_cpp.convert --outtype q4_k_m --outfile llama-2-7b-chat-q4_k_m.gguf /path/to/Llama-2-7b-chat
python -m llama_cpp.server \
  --model /path/to/llama-2-7b-chat-q4_k_m.gguf \
  --host 0.0.0.0 --port 8000 --n_ctx 4096 --chat_format llama-2
```
Set UI: Endpoint `http://localhost:8000`, Model `llama-2-7b-chat`.

### Run the app
macOS/Linux:
```bash
cd prototype_audio_test
source .venv/bin/activate
python app.py
```
Windows (PowerShell):
```powershell
cd prototype_audio_test
.venv\Scripts\Activate.ps1
python app.py
```
Open the printed Gradio URL in your browser.

### Warmup & connection test
- **Warmup starten**: preload Whisper + XTTS (first download 1–2 minutes).
- **LLM Verbindung testen**: quick pong check for endpoint/model.

### UI workflow
1. Open **Experiment** tab.  
2. Set Participant ID, choose scenario (text shown).  
3. Pick language (en/de) – replies + TTS follow this.  
4. Set Big Five/DBQ/BSSS/ERQ and pick the LLM response mode (both vs single).  
5. Adjust endpoint/model if needed (Ollama defaults are prefilled).  
6. Input via mic (push-to-talk) or text box.  
7. Click **Generate response(s)** → one or two replies (depending on mode) with text + TTS.  
8. Optional **Save Condition 1/2**: append row to `results.csv` (no ratings).  
9. Check-in: **Trigger Check-in** gives a short question + optional boredom tip.

### Files & folders
- `results.csv` – saved runs (header auto-created).
- `tmp_audio/` – temporary audio (TTS/inputs). Clear with `rm tmp_audio/*` (macOS/Linux) or `del tmp_audio\*` (PowerShell).
- `persona_rules.json`, `scenarios.json` – content/config.

### Troubleshooting
- Ollama 404: model name must match `ollama list`.
- TTS `BeamSearchScorer`: in `.venv` run `pip install "transformers<4.46"`.
- TTS `weights_only`: `pip install torch==2.5.1 torchaudio==2.5.1`.
- TTS “no speaker provided”: default speaker auto-set; optionally set `TTS_SPEAKER_NAME` or `TTS_SPEAKER_WAV`.
- Slow first reply: warmup; XTTS download once.
- No reply: check endpoint/port; for llama.cpp ensure `--chat_format llama-2`.

### Env vars (quick reference)
- `TTS_SPEAKER_NAME` – name from XTTS speaker list.
- `TTS_SPEAKER_WAV` – path to your reference voice.
- `DEFAULT_ENDPOINT`, `DEFAULT_MODEL` – adjust UI defaults in `settings.py`.

### Clean up audio cache
- macOS/Linux: `rm tmp_audio/*`
- Windows PowerShell: `del tmp_audio\*`

---

## Deutsche Kurzfassung
- Gradio-App vergleicht LLM-Antworten mit/ohne Persona-Hinweise. Audio rein, Whisper-Transkript, XTTS v2 als TTS. UI-Default Englisch, Umschalter auf Deutsch.

### Voraussetzungen
- Python 3.11, Git, Mikrofon; LLM-Server (Ollama empfohlen), Netzwerk für Downloads.

### Setup (macOS/Linux)
```bash
git clone <repo> prototype_audio_test
cd prototype_audio_test
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install --upgrade "transformers<4.46" torch==2.5.1 torchaudio==2.5.1 TTS==0.22.0
pip install gradio faster-whisper soundfile numpy requests TTS
```

### Setup (Windows PowerShell)
```powershell
git clone <repo> prototype_audio_test
cd prototype_audio_test
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install --upgrade "transformers<4.46" torch==2.5.1 torchaudio==2.5.1 TTS==0.22.0
pip install gradio faster-whisper soundfile numpy requests TTS
```
Ollama offiziell macOS/Linux; unter Windows WSL oder anderen OpenAI-kompatiblen Endpoint nutzen.

### LLM-Server
- Ollama: `ollama serve`, `ollama pull llama2:7b-chat` (Endpoint `http://localhost:11434`, Model `llama2:7b-chat`).
- llama.cpp: wie oben mit `--chat_format llama-2`, Endpoint `http://localhost:8000`.

### App starten
```bash
source .venv/bin/activate   # bzw. .venv\Scripts\Activate.ps1
python app.py
```
Gradio-URL im Browser öffnen.

### Nutzung
- Warmup laden, LLM-Verbindung testen.
- Im Tab **Experiment**: ID setzen, Szenario wählen, Sprache (de/en), Slider ausfüllen, Antwortmodus wählen, Endpoint prüfen, Audio oder Text eingeben, **Antwort(en) generieren** drücken.
- Je nach Modus eine oder zwei Antworten (personalisiert / nicht personalisiert) als Text + TTS; optional speichern in `results.csv`.
- Check-in: **Trigger Check-in** liefert Frage + optionalen Langeweile-Tipp.

### Dateien
- `results.csv` (Runs), `tmp_audio/` (temporäre Audios; leeren mit `rm tmp_audio/*` oder `del tmp_audio\*`), `persona_rules.json`, `scenarios.json`.

### Troubleshooting
- 404 bei Ollama: Modellname exakt wie in `ollama list`.
- TTS-Fehler BeamSearchScorer: `pip install "transformers<4.46"`.
- TTS `weights_only`: `pip install "transformers<4.46" torch==2.5.1 torchaudio==2.5.1 TTS==0.22.0`.
- Keine Antwort: Endpoint/Port prüfen; bei llama.cpp `--chat_format llama-2`.
- Langsam: Warmup abwarten; XTTS-Download kann 1–2 min dauern.
