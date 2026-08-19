"""Tests for audio capture — device detection, fallback logic, session state."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from meet_assistant.core.audio_capture import AudioCapture, find_device
from meet_assistant.exceptions import AudioCaptureError


# ── Device discovery ───────────────────────────────────────────────────────────

def test_find_device_returns_none_when_not_found():
    with patch("meet_assistant.core.audio_capture.sd.query_devices") as mock_qd:
        mock_qd.return_value = [
            {"name": "MacBook Pro Microphone", "max_input_channels": 1},
            {"name": "MacBook Pro Speakers", "max_input_channels": 0},
        ]
        assert find_device("BlackHole") is None


def test_find_device_returns_index_when_found():
    with patch("meet_assistant.core.audio_capture.sd.query_devices") as mock_qd:
        mock_qd.return_value = [
            {"name": "MacBook Pro Microphone", "max_input_channels": 1},
            {"name": "BlackHole 2ch", "max_input_channels": 2},
        ]
        assert find_device("BlackHole") == 1


def test_find_device_case_insensitive():
    with patch("meet_assistant.core.audio_capture.sd.query_devices") as mock_qd:
        mock_qd.return_value = [
            {"name": "blackhole 2ch", "max_input_channels": 2},
        ]
        assert find_device("BlackHole") == 0


def test_find_device_skips_output_only_devices():
    with patch("meet_assistant.core.audio_capture.sd.query_devices") as mock_qd:
        mock_qd.return_value = [
            {"name": "BlackHole 2ch", "max_input_channels": 0},  # output only
        ]
        assert find_device("BlackHole") is None


# ── Session state ──────────────────────────────────────────────────────────────

def test_status_returns_inactive_when_idle():
    capture = AudioCapture()
    status = capture.status()
    assert status["active"] is False


def test_is_active_false_when_idle():
    capture = AudioCapture()
    assert capture.is_active is False


def test_stop_raises_when_no_session():
    capture = AudioCapture()
    with pytest.raises(AudioCaptureError, match="No active recording"):
        capture.stop()


def test_double_start_raises():
    capture = AudioCapture()

    mock_stream = MagicMock()

    with patch("meet_assistant.core.audio_capture.find_device", return_value=0), \
         patch("meet_assistant.core.audio_capture.sd.query_devices", return_value={"name": "BlackHole 2ch", "default_samplerate": 16000}), \
         patch("meet_assistant.core.audio_capture.sd.InputStream", return_value=mock_stream):

        capture.start("test-meeting")

        with pytest.raises(AudioCaptureError, match="already in progress"):
            capture.start("another-meeting")

        # Cleanup
        capture._stream = mock_stream
        capture._session.chunks.append(np.zeros((100, 1), dtype="float32"))
        with patch("meet_assistant.core.audio_capture.sf.write"):
            capture.stop()


# ── Fallback logic ─────────────────────────────────────────────────────────────

def test_raises_when_blackhole_missing_and_fallback_disabled(tmp_path):
    capture = AudioCapture()

    with patch("meet_assistant.core.audio_capture.find_device", return_value=None), \
         patch("meet_assistant.core.audio_capture.settings") as mock_settings:

        mock_settings.audio_device_name = "BlackHole 2ch"
        mock_settings.audio_fallback_to_mic = False

        with pytest.raises(AudioCaptureError, match="not found"):
            capture._resolve_device()


def test_falls_back_to_mic_when_blackhole_missing(tmp_path):
    capture = AudioCapture()

    mock_default = {"name": "MacBook Pro Microphone", "default_samplerate": 48000}

    with patch("meet_assistant.core.audio_capture.find_device", return_value=None), \
         patch("meet_assistant.core.audio_capture.sd.query_devices", return_value=mock_default), \
         patch("meet_assistant.core.audio_capture.settings") as mock_settings:

        mock_settings.audio_device_name = "BlackHole 2ch"
        mock_settings.audio_fallback_to_mic = True

        device_index, device_name = capture._resolve_device()
        assert device_index is None
        assert "Microphone" in device_name
