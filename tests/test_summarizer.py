"""Tests for Summarizer — LLM prompt, JSON parsing, fallback, markdown output."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from meet_assistant.core.summarizer import (
    MeetingSummary,
    Summarizer,
    _ensure_action_items,
    _ensure_list,
)
from meet_assistant.exceptions import SummarizationError


# ── Helpers ────────────────────────────────────────────────────────────────────

def test_ensure_list_from_list():
    assert _ensure_list(["a", "b"]) == ["a", "b"]


def test_ensure_list_from_string():
    assert _ensure_list("hello") == ["hello"]


def test_ensure_list_from_none():
    assert _ensure_list(None) == []


def test_ensure_action_items_valid():
    items = [{"owner": "Alice", "description": "Review PR", "deadline": "2026-08-21"}]
    result = _ensure_action_items(items)
    assert result[0]["owner"] == "Alice"
    assert result[0]["description"] == "Review PR"


def test_ensure_action_items_missing_fields():
    items = [{"description": "Do something"}]
    result = _ensure_action_items(items)
    assert result[0]["owner"] == "unknown"
    assert result[0]["deadline"] == ""


def test_ensure_action_items_not_list():
    assert _ensure_action_items("not a list") == []


# ── JSON parsing ───────────────────────────────────────────────────────────────

def _make_summarizer_with_response(response: str) -> Summarizer:
    s = Summarizer()
    s._call_llm = MagicMock(return_value=response)
    return s


def test_parse_valid_json():
    payload = json.dumps({
        "summary": ["Topic A discussed", "Topic B resolved"],
        "decisions": ["Use Python 3.12"],
        "action_items": [{"owner": "Bob", "description": "Deploy by Friday", "deadline": "2026-08-22"}],
        "blockers": ["Waiting on design approval"],
    })
    s = _make_summarizer_with_response(payload)
    result = s.summarise("Some transcript text", meeting_name="standup")

    assert len(result.summary) == 2
    assert result.decisions == ["Use Python 3.12"]
    assert result.action_items[0]["owner"] == "Bob"
    assert result.blockers == ["Waiting on design approval"]
    assert result.meeting_name == "standup"


def test_parse_strips_markdown_fences():
    payload = "```json\n" + json.dumps({"summary": ["Point"], "decisions": [], "action_items": [], "blockers": []}) + "\n```"
    s = _make_summarizer_with_response(payload)
    result = s.summarise("transcript")
    assert result.summary == ["Point"]


def test_parse_fallback_on_invalid_json():
    s = _make_summarizer_with_response("This is not JSON at all.")
    result = s.summarise("transcript")
    assert len(result.summary) == 1
    assert "not JSON" in result.summary[0]


def test_raises_on_empty_transcript():
    s = Summarizer()
    with pytest.raises(SummarizationError, match="empty"):
        s.summarise("   ")


# ── Markdown output ────────────────────────────────────────────────────────────

def test_to_markdown_contains_all_sections():
    ms = MeetingSummary(
        summary=["We discussed the roadmap"],
        decisions=["Ship next week"],
        action_items=[{"owner": "Alice", "description": "Write docs", "deadline": "2026-08-22"}],
        blockers=["Need design sign-off"],
        meeting_name="Planning",
    )
    md = ms.to_markdown()

    assert "# Meeting Summary — Planning" in md
    assert "## Summary" in md
    assert "We discussed the roadmap" in md
    assert "## Key Decisions" in md
    assert "Ship next week" in md
    assert "## Action Items" in md
    assert "**Alice**" in md
    assert "by 2026-08-22" in md
    assert "## Blockers" in md
    assert "Need design sign-off" in md


def test_to_markdown_omits_empty_sections():
    ms = MeetingSummary(
        summary=["Quick sync"],
        decisions=[],
        action_items=[],
        blockers=[],
        meeting_name="Standup",
    )
    md = ms.to_markdown()
    assert "## Key Decisions" not in md
    assert "## Action Items" not in md
    assert "## Blockers" not in md


def test_summarise_and_save_writes_file(tmp_path):
    payload = json.dumps({
        "summary": ["Discussed deployment"],
        "decisions": [],
        "action_items": [],
        "blockers": [],
    })
    s = _make_summarizer_with_response(payload)
    path = s.summarise_and_save("transcript text", output_dir=tmp_path, meeting_name="deploy")

    assert path.exists()
    content = path.read_text()
    assert "Discussed deployment" in content
