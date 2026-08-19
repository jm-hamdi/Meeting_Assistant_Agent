"""Tests for Transcriber — model loading, output format, error handling."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from meet_assistant.core.transcriber import Transcriber, _fmt_time
from meet_assistant.exceptions import TranscriptionError


# ── Helpers ────────────────────────────────────────────────────────────────────

def test_fmt_time_zero():
    assert _fmt_time(0) == "00:00"


def test_fmt_time_seconds():
    assert _fmt_time(65) == "01:05"


def test_fmt_time_large():
    assert _fmt_time(3661) == "61:01"


# ── Error handling ─────────────────────────────────────────────────────────────

def test_transcribe_raises_for_missing_file():
    t = Transcriber()
    with pytest.raises(TranscriptionError, match="not found"):
        t.transcribe("/nonexistent/audio.wav")


def test_transcribe_raises_when_faster_whisper_missing():
    t = Transcriber()
    with patch.dict("sys.modules", {"faster_whisper": None}):
        t._model = None
        with pytest.raises(TranscriptionError, match="not installed"):
            t._load_model()


# ── Output format ──────────────────────────────────────────────────────────────

def test_transcribe_returns_timestamped_lines(sample_wav):
    """Transcriber produces [MM:SS → MM:SS] formatted lines."""
    t = Transcriber()

    seg1 = MagicMock(start=0.0, end=3.5, text="  Hello everyone.  ")
    seg2 = MagicMock(start=4.0, end=7.0, text="Let's get started.")

    mock_model = MagicMock()
    mock_info = MagicMock(language="en", language_probability=0.99)
    mock_model.transcribe.return_value = ([seg1, seg2], mock_info)

    t._model = mock_model

    result = t.transcribe(str(sample_wav))
    lines = result.strip().splitlines()

    assert len(lines) == 2
    assert lines[0] == "[00:00 → 00:03] Hello everyone."
    assert lines[1] == "[00:04 → 00:07] Let's get started."


def test_transcribe_saves_transcript_file(sample_wav):
    """Transcript is written to transcript.txt next to the audio file."""
    t = Transcriber()

    seg = MagicMock(start=0.0, end=2.0, text="Test segment.")
    mock_model = MagicMock()
    mock_info = MagicMock(language="en", language_probability=0.95)
    mock_model.transcribe.return_value = ([seg], mock_info)

    t._model = mock_model
    t.transcribe(str(sample_wav))

    transcript_file = sample_wav.parent / "transcript.txt"
    assert transcript_file.exists()
    assert "Test segment." in transcript_file.read_text()


def test_transcribe_returns_no_speech_when_empty(sample_wav):
    """Returns a friendly message when no speech segments are detected."""
    t = Transcriber()

    mock_model = MagicMock()
    mock_info = MagicMock(language="en", language_probability=0.5)
    mock_model.transcribe.return_value = ([], mock_info)

    t._model = mock_model
    result = t.transcribe(str(sample_wav))

    assert result == "(no speech detected)"


# ── Model lazy loading ─────────────────────────────────────────────────────────

def test_model_loaded_only_once(sample_wav):
    """_load_model is called once and cached for subsequent calls."""
    t = Transcriber()

    mock_model = MagicMock()
    mock_info = MagicMock(language="en", language_probability=0.9)
    mock_model.transcribe.return_value = ([], mock_info)

    with patch("meet_assistant.core.transcriber.settings") as mock_settings, \
         patch("meet_assistant.core.transcriber.WhisperModel", return_value=mock_model) as mock_cls:

        mock_settings.whisper_model_size = "small.en"
        mock_settings.whisper_device = "cpu"
        mock_settings.whisper_compute_type = "int8"

        # Import WhisperModel inside the module so the patch works
        import meet_assistant.core.transcriber as mod
        original = mod.WhisperModel if hasattr(mod, "WhisperModel") else None

        t.transcribe(str(sample_wav))
        t.transcribe(str(sample_wav))

        # Model should only be instantiated once
        assert t._model is mock_model
