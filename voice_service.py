"""Free local speech recognition and synthesis for SafeAI.

Requires ``faster-whisper`` and ``piper-tts``. Both run locally; no audio is
sent to a paid speech API. Piper's Russian voice model path is configured with
PIPER_MODEL_PATH.
"""

import os
import subprocess
import sys
from pathlib import Path


class VoiceServiceError(RuntimeError):
    pass


_whisper_model = None


def _get_whisper_model():
    global _whisper_model
    if _whisper_model is not None:
        return _whisper_model
    try:
        from faster_whisper import WhisperModel
    except ImportError as error:
        raise VoiceServiceError("Не установлена библиотека faster-whisper.") from error

    model_name = os.getenv("WHISPER_MODEL", "base")
    _whisper_model = WhisperModel(model_name, device="cpu", compute_type="int8")
    return _whisper_model


def transcribe(audio_path: str) -> str:
    model = _get_whisper_model()
    try:
        segments, _ = model.transcribe(audio_path, language="ru", vad_filter=True)
        text = " ".join(segment.text.strip() for segment in segments).strip()
    except Exception as error:
        raise VoiceServiceError("Не удалось распознать голосовое сообщение.") from error

    if not text:
        raise VoiceServiceError("Не удалось распознать речь в голосовом сообщении.")
    return text


def synthesize_voice(text: str, output_path: str, voice: str | None = None) -> None:
    """Create an OGG/Opus voice note from text using a local Piper voice."""
    voice_models_dir = Path(__file__).with_name("voice_models")
    default_model_name = (
        "ru_RU-irina-medium.onnx" if voice == "female"
        else "ru_RU-dmitri-medium.onnx"
    )
    model_path = os.getenv("PIPER_MODEL_PATH", str(voice_models_dir / default_model_name))
    if not model_path or not Path(model_path).is_file():
        raise VoiceServiceError("Не настроена локальная модель Piper (PIPER_MODEL_PATH).")

    try:
        import av
    except ImportError as error:
        raise VoiceServiceError("Не установлена библиотека PyAV для кодирования голоса.") from error

    wav_path = f"{output_path}.wav"
    piper_command = os.getenv("PIPER_COMMAND")
    command = [piper_command] if piper_command else [sys.executable, "-m", "piper"]
    try:
        subprocess.run(
            command + [
                "--model", model_path, "--output_file", wav_path,
                # A slightly slower pace and small pauses make a support reply
                # sound calmer without changing its meaning.
                "--length-scale", "1.08", "--sentence-silence", "0.20",
            ],
            input=text[:4000],
            text=True,
            check=True,
            capture_output=True,
            timeout=90,
        )

        input_container = av.open(wav_path)
        output_container = av.open(output_path, mode="w", format="ogg")
        output_stream = output_container.add_stream("libopus", rate=48000)
        output_stream.layout = "mono"
        for frame in input_container.decode(audio=0):
            for packet in output_stream.encode(frame):
                output_container.mux(packet)
        for packet in output_stream.encode(None):
            output_container.mux(packet)
        input_container.close()
        output_container.close()
    except (OSError, subprocess.SubprocessError, Exception) as error:
        raise VoiceServiceError("Не удалось озвучить ответ.") from error
    finally:
        Path(wav_path).unlink(missing_ok=True)
