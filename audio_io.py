import os
import uuid
from pathlib import Path
from typing import Optional, Tuple
import wave
import contextlib

from faster_whisper import WhisperModel
from TTS.api import TTS
try:
    from torch.serialization import add_safe_globals
    from TTS.tts.configs.xtts_config import XttsConfig
except Exception:  # pragma: no cover - defensive import
    add_safe_globals = None  # type: ignore
    XttsConfig = None  # type: ignore

from settings import TMP_DIR

# Lazy globals
whisper_model: Optional[WhisperModel] = None
tts_model: Optional[TTS] = None
tts_default_speaker: Optional[str] = None


def get_whisper() -> WhisperModel:
    global whisper_model
    if whisper_model is None:
        whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
    return whisper_model


def get_tts() -> Tuple[TTS, Optional[str]]:
    global tts_model, tts_default_speaker
    if tts_model is None:
        try:
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
                    'TTS-Init fehlgeschlagen: Bitte `pip install "transformers<4.46"` im .venv ausfuehren.'
                ) from exc
            if "Weights only load failed" in msg or "weights_only" in msg:
                raise RuntimeError(
                    "TTS-Init fehlgeschlagen (weights_only). Versuche `pip install torch==2.5.1` im .venv "
                    "oder stelle sicher, dass die XTTS-Checkpoint-Datei vertrauenswürdig ist."
                ) from exc
            raise
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


def transcribe_audio(audio_path: Optional[str], language_hint: Optional[str] = None) -> Tuple[str, Optional[str], Optional[str]]:
    if not audio_path or not Path(audio_path).exists():
        return "", "No audio captured. Using scenario text instead.", None
    lang = language_hint if language_hint in ("en", "de") else None
    try:
        model = get_whisper()
        segments, info = model.transcribe(audio_path, beam_size=5, language=lang, task="transcribe")
        text = " ".join([seg.text.strip() for seg in segments]).strip()
        detected_lang = getattr(info, "language", None)
        return text, None, detected_lang
    except Exception as exc:  # pragma: no cover - runtime safeguard
        return "", f"Transcription failed: {exc}", None


def synthesize_speech(text: str, language: str, tag: str) -> Tuple[Optional[str], Optional[str]]:
    if not text or not str(text).strip():
        return None, "No text provided for TTS."
    tts, speaker = get_tts()
    out_path = TMP_DIR / f"{tag}_{uuid.uuid4().hex}.wav"
    tts_kwargs = {"text": text, "language": language, "file_path": str(out_path)}
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
        fallback_path = _write_silence_wav(tag)
        return fallback_path, f"TTS error: {exc}"


def _write_silence_wav(tag: str, duration_sec: float = 1.0, sample_rate: int = 16000) -> str:
    """Create a short silent WAV as a fallback to avoid hard failures."""
    frames = int(duration_sec * sample_rate)
    out_path = TMP_DIR / f"{tag}_silent_{uuid.uuid4().hex}.wav"
    with contextlib.closing(wave.open(str(out_path), "w")) as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit PCM
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00\x00" * frames)
    return str(out_path)


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
