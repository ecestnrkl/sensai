import os
import threading
import uuid
from pathlib import Path
from typing import Generator, Optional, Tuple
import wave
import contextlib

from faster_whisper import WhisperModel  # type: ignore[import-untyped]
from TTS.api import TTS  # type: ignore[import-untyped]
try:
    from torch.serialization import add_safe_globals
    from TTS.tts.configs.xtts_config import XttsConfig  # type: ignore[import-untyped]
except Exception:  # pragma: no cover - defensive import
    add_safe_globals = None  # type: ignore[assignment]
    XttsConfig = None

from settings import TMP_DIR


class AudioModels:
    """Thread-safe singleton for managing Whisper and TTS models."""
    
    _instance: Optional['AudioModels'] = None
    _lock = threading.Lock()
    
    def __init__(self) -> None:
        """Private constructor. Use get_instance() instead."""
        self._whisper_model: Optional[WhisperModel] = None
        self._tts_model: Optional[TTS] = None
        self._tts_default_speaker: Optional[str] = None
        self._whisper_lock = threading.Lock()
        self._tts_lock = threading.Lock()
    
    @classmethod
    def get_instance(cls) -> 'AudioModels':
        """Get the singleton instance (thread-safe)."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    def get_whisper(self) -> WhisperModel:
        """Get or initialize Whisper model (thread-safe)."""
        if self._whisper_model is None:
            with self._whisper_lock:
                if self._whisper_model is None:
                    self._whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
        return self._whisper_model
    
    def get_tts(self) -> Tuple[TTS, Optional[str]]:
        """Get or initialize TTS model and default speaker (thread-safe)."""
        if self._tts_model is None:
            with self._tts_lock:
                if self._tts_model is None:
                    try:
                        if add_safe_globals is not None and XttsConfig:
                            try:
                                add_safe_globals([XttsConfig])
                            except Exception:
                                pass
                        self._tts_model = TTS(
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
                        sm = self._tts_model.synthesizer.tts_model.speaker_manager
                        if sm and getattr(sm, "speakers", None):
                            names = list(sm.speakers.keys())
                            if names:
                                self._tts_default_speaker = names[0]
                    except Exception:
                        self._tts_default_speaker = None
                    env_speaker = os.getenv("TTS_SPEAKER_NAME")
                    if env_speaker:
                        self._tts_default_speaker = env_speaker
        return self._tts_model, self._tts_default_speaker


# Convenience functions for backward compatibility
def get_whisper() -> WhisperModel:
    """Get Whisper model instance."""
    return AudioModels.get_instance().get_whisper()


def get_tts() -> Tuple[TTS, Optional[str]]:
    """Get TTS model instance and default speaker."""
    return AudioModels.get_instance().get_tts()


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
            sm = tts.synthesizer.tts_model.speaker_manager
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


def warm_up_models() -> Generator[str, None, None]:
    """Warm up models with progress updates for Gradio UI."""
    yield "Starting warmup..."
    
    try:
        yield "Loading Whisper model (speech-to-text)..."
        get_whisper()
        yield "✓ Whisper loaded successfully"
    except Exception as exc:  # pragma: no cover - runtime safeguard
        yield f"✗ Whisper error: {exc}"
        return
    
    try:
        yield "Loading XTTS model (text-to-speech). First download may take 1-2 minutes..."
        get_tts()
        yield "✓ XTTS loaded successfully. Models ready!"
    except Exception as exc:  # pragma: no cover - runtime safeguard
        yield f"✗ TTS error: {exc}"
