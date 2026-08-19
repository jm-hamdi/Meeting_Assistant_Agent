"""Shared pytest fixtures."""

from __future__ import annotations

import numpy as np
import pytest
import soundfile as sf


@pytest.fixture
def sample_wav(tmp_path):
    """Generate a 3-second silent WAV file at 16000 Hz for testing."""
    path = tmp_path / "sample.wav"
    sample_rate = 16000
    duration = 3
    audio = np.zeros((sample_rate * duration,), dtype="float32")
    sf.write(str(path), audio, sample_rate)
    return path


@pytest.fixture
def sample_wav_with_tone(tmp_path):
    """Generate a 3-second 440 Hz sine wave WAV for testing (non-silent)."""
    path = tmp_path / "tone.wav"
    sample_rate = 16000
    duration = 3
    t = np.linspace(0, duration, sample_rate * duration, endpoint=False)
    audio = (0.3 * np.sin(2 * np.pi * 440 * t)).astype("float32")
    sf.write(str(path), audio, sample_rate)
    return path
