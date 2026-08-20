"""Summarization tool — extracts summary and action items from a transcript."""

from __future__ import annotations

from smolagents import tool

from meet_assistant.core.summarizer import summarizer
from meet_assistant.exceptions import SummarizationError


@tool
def summarize_transcript(transcript: str, meeting_name: str = "") -> str:
    """Summarise a meeting transcript using the local LLM.

    Extracts: summary bullets, key decisions, action items (owner + deadline), and blockers.
    The summary is saved as summary.md in the meeting output folder if meeting_name matches
    an existing session; otherwise it is returned as text only.

    Args:
        transcript:   Full transcript text (timestamped or plain).
        meeting_name: Optional meeting name/slug used to locate the output folder.

    Returns:
        Formatted markdown summary with action items.
    """
    try:
        summary = summarizer.summarise(transcript, meeting_name=meeting_name)
        return summary.to_markdown()
    except SummarizationError as exc:
        return f"Summarisation failed: {exc}"
    except Exception as exc:
        return f"Unexpected error: {exc}"
