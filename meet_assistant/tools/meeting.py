"""Meeting orchestrator — runs the full pipeline end-to-end."""

from __future__ import annotations

import json
import time
from pathlib import Path

from smolagents import tool

from meet_assistant.core.audio_capture import audio_capture
from meet_assistant.core.summarizer import summarizer
from meet_assistant.core.task_writer import task_writer
from meet_assistant.core.transcriber import transcriber
from meet_assistant.exceptions import MeetAssistError


@tool
def run_full_pipeline(duration_seconds: int = 0, meeting_name: str = "") -> str:
    """Run the complete meeting pipeline: record → transcribe → summarise → create tasks.

    If duration_seconds > 0, records for exactly that many seconds then processes automatically.
    If duration_seconds = 0, starts recording and returns — call stop_recording() when done,
    then call process_recording() to finish the pipeline.

    Args:
        duration_seconds: How long to record in seconds. 0 = start only (manual stop).
        meeting_name:     Optional slug for the output folder.

    Returns:
        Paths to all generated artifacts and a summary of action items found.
    """
    try:
        session = audio_capture.start(meeting_name=meeting_name)
    except MeetAssistError as exc:
        return f"Failed to start recording: {exc}"

    if duration_seconds == 0:
        return (
            f"Recording started — {session.device_name}\n"
            f"Output: {session.output_dir}\n"
            "Call stop_recording() when done, then process_recording() to finish."
        )

    # Timed recording
    try:
        _wait(duration_seconds, session.meeting_name)
        audio_path = audio_capture.stop()
    except MeetAssistError as exc:
        return f"Recording failed: {exc}"

    return _process(audio_path, session.output_dir, session.meeting_name)


@tool
def process_recording(audio_path: str = "", meeting_name: str = "") -> str:
    """Transcribe, summarise, and create tasks from an audio file.

    Use this after stop_recording() to finish the pipeline, or pass any existing WAV file.

    Args:
        audio_path:   Path to the WAV file. If empty, uses the last stopped recording.
        meeting_name: Meeting name for output labelling.

    Returns:
        Paths to generated files and action item count.
    """
    if not audio_path:
        return "No audio_path provided. Pass the path returned by stop_recording()."

    path = Path(audio_path)
    if not path.exists():
        return f"Audio file not found: {audio_path}"

    output_dir = path.parent
    name = meeting_name or output_dir.name

    return _process(path, output_dir, name)


# ── Shared pipeline logic ──────────────────────────────────────────────────────

def _process(audio_path: Path, output_dir: Path, meeting_name: str) -> str:
    results: dict[str, str] = {"audio": str(audio_path)}

    # 1 — Transcribe
    try:
        transcript = transcriber.transcribe(str(audio_path))
        results["transcript"] = str(output_dir / "transcript.txt")
    except Exception as exc:
        return f"Transcription failed: {exc}\nAudio saved at: {audio_path}"

    # 2 — Summarise
    try:
        meeting_summary = summarizer.summarise(transcript, meeting_name=meeting_name)
        summary_path = output_dir / "summary.md"
        summary_path.write_text(meeting_summary.to_markdown(), encoding="utf-8")
        results["summary"] = str(summary_path)
    except Exception as exc:
        return (
            f"Summarisation failed: {exc}\n"
            f"Transcript saved at: {results['transcript']}"
        )

    # 3 — Create tasks
    try:
        task_results = task_writer.write(
            action_items=meeting_summary.action_items,
            output_dir=output_dir,
            meeting_name=meeting_name,
        )
        results["tasks"] = task_results.get("markdown", "")
    except Exception as exc:
        results["tasks"] = f"Task writing failed: {exc}"

    # Build response
    n_tasks = len(meeting_summary.action_items)
    lines = [
        f"Pipeline complete — {meeting_name}",
        f"  Audio      : {results['audio']}",
        f"  Transcript : {results['transcript']}",
        f"  Summary    : {results['summary']}",
        f"  Tasks      : {results['tasks']}",
        f"  Action items found: {n_tasks}",
    ]

    if meeting_summary.action_items:
        lines.append("\nAction items:")
        for item in meeting_summary.action_items:
            owner = item.get("owner", "unknown")
            desc = item.get("description", "")
            deadline = item.get("deadline", "")
            deadline_str = f" (by {deadline})" if deadline else ""
            lines.append(f"  • {owner} — {desc}{deadline_str}")

    return "\n".join(lines)


def _wait(seconds: int, meeting_name: str) -> None:
    """Block for *seconds* with a simple countdown."""
    try:
        from rich.progress import Progress, SpinnerColumn, TimeElapsedColumn
        with Progress(SpinnerColumn(), *Progress.get_default_columns(), TimeElapsedColumn()) as progress:
            task = progress.add_task(f"[cyan]Recording {meeting_name}…", total=seconds)
            elapsed = 0
            while elapsed < seconds:
                time.sleep(1)
                elapsed += 1
                progress.update(task, advance=1)
    except ImportError:
        # Fallback if rich is not available
        print(f"Recording for {seconds}s…")
        time.sleep(seconds)
