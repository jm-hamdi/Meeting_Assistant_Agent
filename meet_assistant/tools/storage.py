"""Storage tools — browse and retrieve past meeting sessions."""

from __future__ import annotations

from pathlib import Path

from smolagents import tool

from meet_assistant.settings import settings


@tool
def list_meetings() -> str:
    """List all past meeting sessions in the outputs directory.

    Returns:
        A formatted list of meeting names, dates, and available files.
    """
    output_dir = Path(settings.output_dir)
    if not output_dir.exists():
        return "No meetings found — outputs/ directory does not exist yet."

    sessions = sorted(
        [d for d in output_dir.iterdir() if d.is_dir() and not d.name.startswith(".")],
        reverse=True,
    )

    if not sessions:
        return "No meeting sessions found in outputs/."

    lines = [f"Found {len(sessions)} meeting session(s):\n"]
    for session in sessions:
        files = [f.name for f in session.iterdir() if f.is_file()]
        file_list = ", ".join(sorted(files)) if files else "empty"
        lines.append(f"  {session.name}")
        lines.append(f"    Files: {file_list}")

    return "\n".join(lines)


@tool
def get_meeting(meeting_name: str) -> str:
    """Retrieve details and content for a specific past meeting session.

    Args:
        meeting_name: The meeting folder name (e.g. '2026-08-20_standup').

    Returns:
        Summary of the meeting including file paths and summary content if available.
    """
    output_dir = Path(settings.output_dir)
    session_dir = output_dir / meeting_name

    if not session_dir.exists():
        # Try partial match
        matches = [d for d in output_dir.iterdir() if d.is_dir() and meeting_name.lower() in d.name.lower()]
        if not matches:
            return f"Meeting '{meeting_name}' not found in {output_dir}."
        if len(matches) == 1:
            session_dir = matches[0]
        else:
            names = ", ".join(m.name for m in matches)
            return f"Multiple matches found: {names}\nBe more specific."

    lines = [f"Meeting: {session_dir.name}", f"Location: {session_dir}\n"]

    files = sorted(session_dir.iterdir(), key=lambda f: f.name)
    for f in files:
        if not f.is_file():
            continue
        size_kb = round(f.stat().st_size / 1024, 1)
        lines.append(f"  {f.name} ({size_kb} KB)")

    # Show summary content if available
    summary_path = session_dir / "summary.md"
    if summary_path.exists():
        lines.append("\n--- Summary ---")
        lines.append(summary_path.read_text(encoding="utf-8"))

    # Show tasks if available
    tasks_path = session_dir / "tasks.md"
    if tasks_path.exists():
        lines.append("\n--- Tasks ---")
        lines.append(tasks_path.read_text(encoding="utf-8"))

    return "\n".join(lines)
