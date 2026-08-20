"""Task creation tool — writes action items to markdown, Notion, and/or GitHub."""

from __future__ import annotations

import json

from smolagents import tool

from meet_assistant.core.task_writer import task_writer
from meet_assistant.exceptions import TaskWriterError


@tool
def create_tasks(
    action_items_json: str,
    output_dir: str,
    meeting_name: str = "",
    push_to_notion: bool = False,
    push_to_github: bool = False,
) -> str:
    """Write meeting action items to tasks.md and optionally to Notion or GitHub Issues.

    Args:
        action_items_json: JSON array of action items. Each item must have:
                           {"owner": str, "description": str, "deadline": str}
                           Example: '[{"owner": "Alice", "description": "Review PR", "deadline": "2026-08-21"}]'
        output_dir:        Path to the meeting session folder where tasks.md will be saved.
        meeting_name:      Meeting name/slug included in the file front-matter.
        push_to_notion:    If true, create a Notion page per action item (requires MEETASSIST_NOTION_TOKEN).
        push_to_github:    If true, create a GitHub Issue per action item (requires MEETASSIST_GITHUB_TOKEN).

    Returns:
        Summary of what was created and where.
    """
    try:
        action_items = json.loads(action_items_json)
    except json.JSONDecodeError as exc:
        return f"Invalid action_items_json — must be a valid JSON array: {exc}"

    if not isinstance(action_items, list):
        return "Invalid action_items_json — expected a JSON array."

    try:
        results = task_writer.write(
            action_items=action_items,
            output_dir=output_dir,
            meeting_name=meeting_name,
            push_to_notion=push_to_notion,
            push_to_github=push_to_github,
        )
    except TaskWriterError as exc:
        return f"Task creation failed: {exc}"
    except Exception as exc:
        return f"Unexpected error: {exc}"

    lines = [f"Tasks created ({len(action_items)} item(s)):"]
    for dest, result in results.items():
        lines.append(f"  {dest:<10} → {result}")
    return "\n".join(lines)
