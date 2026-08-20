"""Pipeline and storage tests — E2E tests require real audio hardware."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import soundfile as sf

from meet_assistant.tools.storage import get_meeting, list_meetings


# ── Storage tools ──────────────────────────────────────────────────────────────

def test_list_meetings_no_output_dir(tmp_path):
    with patch("meet_assistant.tools.storage.settings") as mock_settings:
        mock_settings.output_dir = str(tmp_path / "nonexistent")
        result = list_meetings()
    assert "No meetings found" in result


def test_list_meetings_empty_dir(tmp_path):
    with patch("meet_assistant.tools.storage.settings") as mock_settings:
        mock_settings.output_dir = str(tmp_path)
        result = list_meetings()
    assert "No meeting sessions found" in result


def test_list_meetings_shows_sessions(tmp_path):
    (tmp_path / "2026-08-20_standup").mkdir()
    (tmp_path / "2026-08-20_standup" / "audio.wav").touch()
    (tmp_path / "2026-08-20_standup" / "transcript.txt").touch()
    (tmp_path / "2026-08-19_planning").mkdir()

    with patch("meet_assistant.tools.storage.settings") as mock_settings:
        mock_settings.output_dir = str(tmp_path)
        result = list_meetings()

    assert "2026-08-20_standup" in result
    assert "2026-08-19_planning" in result
    assert "audio.wav" in result


def test_get_meeting_not_found(tmp_path):
    with patch("meet_assistant.tools.storage.settings") as mock_settings:
        mock_settings.output_dir = str(tmp_path)
        result = get_meeting("nonexistent-meeting")
    assert "not found" in result


def test_get_meeting_exact_match(tmp_path):
    session = tmp_path / "2026-08-20_standup"
    session.mkdir()
    (session / "audio.wav").write_bytes(b"fake")
    (session / "summary.md").write_text("# Summary\n- Topic A", encoding="utf-8")

    with patch("meet_assistant.tools.storage.settings") as mock_settings:
        mock_settings.output_dir = str(tmp_path)
        result = get_meeting("2026-08-20_standup")

    assert "2026-08-20_standup" in result
    assert "audio.wav" in result
    assert "Topic A" in result


def test_get_meeting_partial_match(tmp_path):
    session = tmp_path / "2026-08-20_standup"
    session.mkdir()
    (session / "transcript.txt").write_text("Hello", encoding="utf-8")

    with patch("meet_assistant.tools.storage.settings") as mock_settings:
        mock_settings.output_dir = str(tmp_path)
        result = get_meeting("standup")

    assert "2026-08-20_standup" in result


def test_get_meeting_shows_tasks(tmp_path):
    session = tmp_path / "2026-08-20_review"
    session.mkdir()
    (session / "tasks.md").write_text("- [ ] **Alice** — Ship it", encoding="utf-8")

    with patch("meet_assistant.tools.storage.settings") as mock_settings:
        mock_settings.output_dir = str(tmp_path)
        result = get_meeting("2026-08-20_review")

    assert "Alice" in result
    assert "Ship it" in result


# ── Pipeline orchestration (mocked) ───────────────────────────────────────────

def test_process_recording_missing_file():
    from meet_assistant.tools.meeting import process_recording
    result = process_recording(audio_path="/nonexistent/audio.wav")
    assert "not found" in result


def test_process_recording_no_path():
    from meet_assistant.tools.meeting import process_recording
    result = process_recording(audio_path="")
    assert "No audio_path" in result


def test_run_full_pipeline_zero_duration_starts_recording(tmp_path):
    from meet_assistant.tools.meeting import run_full_pipeline

    mock_session = MagicMock()
    mock_session.device_name = "BlackHole 2ch"
    mock_session.output_dir = tmp_path
    mock_session.meeting_name = "test"

    with patch("meet_assistant.tools.meeting.audio_capture") as mock_capture:
        mock_capture.start.return_value = mock_session
        result = run_full_pipeline(duration_seconds=0, meeting_name="test")

    assert "Recording started" in result
    assert "stop_recording" in result


def test_run_full_pipeline_timed(tmp_path, sample_wav):
    from meet_assistant.tools.meeting import run_full_pipeline

    mock_session = MagicMock()
    mock_session.device_name = "BlackHole 2ch"
    mock_session.output_dir = tmp_path
    mock_session.meeting_name = "test-timed"

    mock_summary = MagicMock()
    mock_summary.action_items = [{"owner": "Alice", "description": "Do thing", "deadline": ""}]
    mock_summary.to_markdown.return_value = "# Summary"

    with patch("meet_assistant.tools.meeting.audio_capture") as mock_capture, \
         patch("meet_assistant.tools.meeting.transcriber") as mock_transcriber, \
         patch("meet_assistant.tools.meeting.summarizer") as mock_summarizer, \
         patch("meet_assistant.tools.meeting.task_writer") as mock_task_writer, \
         patch("meet_assistant.tools.meeting._wait"):

        mock_capture.start.return_value = mock_session
        mock_capture.stop.return_value = sample_wav
        mock_transcriber.transcribe.return_value = "Hello everyone."
        mock_summarizer.summarise.return_value = mock_summary
        mock_task_writer.write.return_value = {"markdown": str(tmp_path / "tasks.md")}

        result = run_full_pipeline(duration_seconds=5, meeting_name="test-timed")

    assert "Pipeline complete" in result
    assert "Alice" in result


# ── E2E (requires real audio hardware) ────────────────────────────────────────

@pytest.mark.e2e
def test_e2e_record_and_transcribe(tmp_path):
    """Records 3 seconds of real audio and transcribes it. Requires microphone access."""
    import sounddevice as sd

    # Skip if no input device available
    try:
        sd.query_devices(kind="input")
    except Exception:
        pytest.skip("No audio input device available.")

    from meet_assistant.core.audio_capture import AudioCapture
    from meet_assistant.core.transcriber import Transcriber

    capture = AudioCapture()
    session = capture.start(meeting_name="e2e-test")
    time_start = __import__("time").time()

    import time
    time.sleep(3)

    audio_path = capture.stop()
    assert audio_path.exists()
    assert audio_path.stat().st_size > 0

    t = Transcriber()
    result = t.transcribe(str(audio_path))
    assert isinstance(result, str)
