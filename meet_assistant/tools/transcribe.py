"""Transcription tool — converts an audio file to timestamped text using Whisper."""

from __future__ import annotations

from smolagents import tool

from meet_assistant.core.transcriber import transcriber
from meet_assistant.exceptions import TranscriptionError


@tool
def transcribe_audio(audio_path: str, language: str = "en") -> str:
    """Transcribe a WAV, MP3, or M4A file to text using local faster-whisper.

    The transcript is saved as transcript.txt in the same folder as the audio file.
    On first use, the Whisper model (~244 MB) is downloaded automatically.

    Args:
        audio_path: Absolute or relative path to the audio file.
        language:   ISO 639-1 language code (default: 'en'). Use 'auto' to auto-detect.

    Returns:
        Full timestamped transcript, one line per speech segment.
    """
    try:
        lang = None if language == "auto" else language
        return transcriber.transcribe(audio_path, language=lang or "en")
    except TranscriptionError as exc:
        return f"Transcription failed: {exc}"
    except Exception as exc:
        return f"Unexpected error during transcription: {exc}"
