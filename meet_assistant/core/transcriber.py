"""Transcriber — converts audio files to text using faster-whisper (local, no cloud)."""

from __future__ import annotations

import logging
from pathlib import Path

from meet_assistant.exceptions import TranscriptionError
from meet_assistant.settings import settings

logger = logging.getLogger("meet_assistant.core.transcriber")


class Transcriber:
    """Wraps faster-whisper with lazy model loading and structured output."""

    def __init__(self) -> None:
        self._model = None  # loaded on first use

    def _load_model(self):
        if self._model is not None:
            return self._model

        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise TranscriptionError(
                "faster-whisper is not installed. Run: pip install faster-whisper"
            ) from exc

        model_size = settings.whisper_model_size
        device = settings.whisper_device
        compute_type = settings.whisper_compute_type

        # Resolve 'auto' → 'cpu' on macOS (no CUDA)
        if device == "auto":
            try:
                import torch
                device = "cuda" if torch.cuda.is_available() else "cpu"
            except ImportError:
                device = "cpu"

        logger.info("Loading Whisper model '%s' on %s (%s)…", model_size, device, compute_type)
        logger.info("First run downloads ~244 MB to ~/.cache/huggingface/hub/ — subsequent runs are offline.")

        self._model = WhisperModel(model_size, device=device, compute_type=compute_type)
        logger.info("Whisper model loaded.")
        return self._model

    def transcribe(self, audio_path: str | Path, language: str = "en") -> str:
        """Transcribe *audio_path* and return full timestamped text.

        Returns a string with one line per segment:
            [00:00 → 00:05] Hello everyone, let's get started.
        """
        path = Path(audio_path)
        if not path.exists():
            raise TranscriptionError(f"Audio file not found: {path}")

        model = self._load_model()

        try:
            segments, info = model.transcribe(
                str(path),
                language=language,
                beam_size=5,
                vad_filter=True,          # skip silence automatically
                vad_parameters={"min_silence_duration_ms": 500},
            )
            logger.info(
                "Detected language: %s (%.0f%% confidence)",
                info.language, info.language_probability * 100,
            )
        except Exception as exc:
            raise TranscriptionError(f"Transcription failed: {exc}") from exc

        lines: list[str] = []
        for seg in segments:
            start = _fmt_time(seg.start)
            end = _fmt_time(seg.end)
            lines.append(f"[{start} → {end}] {seg.text.strip()}")

        if not lines:
            return "(no speech detected)"

        transcript = "\n".join(lines)

        # Save alongside the audio file
        transcript_path = path.parent / "transcript.txt"
        transcript_path.write_text(transcript, encoding="utf-8")
        logger.info("Transcript saved → %s", transcript_path)

        return transcript

    def transcribe_to_file(self, audio_path: str | Path, language: str = "en") -> Path:
        """Transcribe and return the path to the saved transcript file."""
        transcript = self.transcribe(audio_path, language)
        path = Path(audio_path)
        transcript_path = path.parent / "transcript.txt"
        transcript_path.write_text(transcript, encoding="utf-8")
        return transcript_path


def _fmt_time(seconds: float) -> str:
    """Format seconds as MM:SS."""
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m:02d}:{s:02d}"


# ── Module-level singleton ─────────────────────────────────────────────────────
transcriber = Transcriber()
