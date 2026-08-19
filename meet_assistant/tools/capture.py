"""Audio capture tools — start, stop, and check recording status."""

from __future__ import annotations

from smolagents import tool

from meet_assistant.core.audio_capture import audio_capture
from meet_assistant.exceptions import AudioCaptureError


@tool
def start_recording(meeting_name: str = "") -> str:
    """Start capturing audio from BlackHole loopback (or microphone if BlackHole is not installed).

    Args:
        meeting_name: Optional slug for the output folder (e.g. 'standup', 'client-call').
                      Auto-generated from current date/time if empty.

    Returns:
        Confirmation message with the output directory path.
    """
    try:
        session = audio_capture.start(meeting_name=meeting_name)
        return (
            f"Recording started.\n"
            f"  Device  : {session.device_name}\n"
            f"  Rate    : {session.sample_rate} Hz\n"
            f"  Output  : {session.output_dir}\n"
            f"Call stop_recording() when the meeting is over."
        )
    except AudioCaptureError as exc:
        return f"Failed to start recording: {exc}"


@tool
def stop_recording() -> str:
    """Stop the active audio recording and save the WAV file.

    Returns:
        Path to the saved WAV file, or an error message.
    """
    try:
        audio_path = audio_capture.stop()
        return f"Recording saved → {audio_path}"
    except AudioCaptureError as exc:
        return f"Failed to stop recording: {exc}"


@tool
def recording_status() -> str:
    """Check whether a recording is currently active.

    Returns:
        Status summary including device, elapsed time, and output path.
    """
    status = audio_capture.status()
    if not status["active"]:
        return "No active recording."
    return (
        f"Recording in progress.\n"
        f"  Meeting : {status['meeting_name']}\n"
        f"  Device  : {status['device']}\n"
        f"  Elapsed : {status['elapsed_seconds']}s\n"
        f"  Output  : {status['output_dir']}"
    )
