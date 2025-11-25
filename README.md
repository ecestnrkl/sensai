# Audio Personality Prompting Prototype
Lokaler Gradio-Harness, der LLM-Antworten mit/ohne Persona Conditioning vergleicht. Nutzt Mikrofonaufnahme, Whisper-Transkription und Coqui XTTS v2 (TTS).

## Installation
```bash
cd /prototype_audio_test
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install "transformers<4.46"  # nötig, weil TTS noch BeamSearchScorer erwartet
pip install gradio faster-whisper soundfile numpy requests TTS
```

## Schnellstart (2 Terminals)
1) **LLM-Server starten** (Option A: llama.cpp mit Llama-2-7b-chat, Option B: Ollama – Standard im UI)  
2) **App starten**  
```bash
source .venv/bin/activate
python app.py
```
3) Im Browser: erst Tab **Pre-Test Survey** ausfüllen und speichern, dann Tab **Experiment** ausfüllen und **Run both conditions** drücken.  
4) Nach dem Abspielen pro Condition die Ratings setzen und speichern.

## Option A: Llama-2-7b-chat lokal (llama.cpp, CPU)
Terminal A: Modell bereitstellen und Server starten.
```bash
# 1) Llama 2 Chat laden (Meta-Instruktionen) nach /Users/<you>/.llama/checkpoints/Llama-2-7b-chat
cd /Users/<you>/.llama/checkpoints/Llama-2-7b-chat
python -m venv .venv && source .venv/bin/activate
python -m pip install --upgrade pip
pip install llama-cpp-python

# 2) In GGUF konvertieren (Q4_K_M, CPU-freundlich)
python -m llama_cpp.convert --outtype q4_k_m --outfile llama-2-7b-chat-q4_k_m.gguf .

# 3) OpenAI-kompatiblen Server starten (läuft weiter)
python -m llama_cpp.server \
  --model /Users/<you>/.llama/checkpoints/Llama-2-7b-chat/llama-2-7b-chat-q4_k_m.gguf \
  --host 0.0.0.0 --port 8000 --n_ctx 4096 --chat_format llama-2
```
Terminal B: App starten (siehe Schnellstart).

**UI-Einstellungen für diese Option**
- Endpoint URL: `http://localhost:8000` (UI ist standardmäßig auf Ollama gestellt; hier bitte anpassen)
- Model Name: `llama2:7b-chat`
- Button **LLM Verbindung testen** zeigt sofort, ob der Endpoint erreichbar ist.

## Option B: Ollama (einfachster Weg)
Terminal A:
```bash
brew install ollama          # falls noch nicht vorhanden
ollama serve                 # Server offen lassen
ollama pull llama2:7b-chat        # lädt Llama-2-Chat 7B
```
Terminal B: App starten.

**UI-Einstellungen für Ollama**
- Endpoint URL: `http://localhost:11434` (Default im UI)
- Model Name: exakt wie in `ollama list` (Default: `llama2:7b-chat`)
- Bei 404: Modellname prüfen, exakt eintragen und erneut **LLM Verbindung testen**.

## Bedienung & Hinweise
- **Endpoint/Modell**: Das Tool erkennt automatisch Ollama (`/api/chat`) vs. OpenAI-kompatibel (`/v1/chat/completions`). Auch Basispfade wie `http://localhost:8000/v1` werden bereinigt.
- **Warmup**: Button **Warmup starten** lädt Whisper + XTTS vor. Der erste XTTS-Download (~1–2 GB) kann 1–2 Minuten dauern; danach ist TTS schnell.
- **Audio**: Mikrofon aufnehmen (Push-to-talk), Whisper transkribiert. Fällt Transkription aus, wird der Scenario-Text genutzt.
- **TTS**: `tts_models/multilingual/multi-dataset/xtts_v2`. Multi-Speaker: Default-Speaker wird automatisch gesetzt; mit `TTS_SPEAKER_NAME="<Name aus speakers.json>"` oder `TTS_SPEAKER_WAV=/pfad/zu/voice.wav` kannst du explizit steuern.
- **Logs**: Ratings/Antworten landen in `results.csv` (Header wird automatisch angelegt).
- **Leistung**: Whisper int8 + XTTS v2 laufen auf CPU. Erster Lauf lädt Modelle und ist langsamer.

## Troubleshooting
- **LLM Verbindung testen** im UI nutzen, bevor du aufnimmst. Meldet klaren Fehlertext inkl. URL.
- 404 bei Ollama: Modellname stimmt nicht (`ollama list` prüfen).
- Keine Antwort: Läuft der Server? Richtiger Port? Bei llama.cpp muss `--chat_format llama-2` gesetzt sein.
- Doppelte Pfade wie `/v1/v1/...` werden automatisch korrigiert; trage nur die Basis-URL ein.
- Antworten dauern zu lange: Generations sind auf ~200 Tokens begrenzt. Passe `MAX_GENERATION_TOKENS` in `app.py` an, falls nötig.
- Erster TTS-Call hängt: Vorher **Warmup starten** drücken (oder einmalig TTS im Code laden). Der Download kann je nach Verbindung >1 Minute dauern.
- TTS-Importfehler `BeamSearchScorer`: Im `.venv` `pip install "transformers<4.46"` ausführen und die App neu starten.
- TTS weights_only/Checkpoint-Fehler: Falls Warmup wegen `weights_only` fehlschlägt, `pip install torch==2.5.1` im `.venv` probieren. Nur Checkpoints aus vertrauenswürdiger Quelle nutzen.
- TTS meldet „no speaker provided“: Default-Speaker wird nun automatisch gesetzt. Falls du eine bestimmte Stimme willst, setze `TTS_SPEAKER_NAME` oder `TTS_SPEAKER_WAV`.
