"""Tests for TaskWriter — markdown format, Notion/GitHub integration guards."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from meet_assistant.core.task_writer import TaskWriter


SAMPLE_ITEMS = [
    {"owner": "Alice", "description": "Review the PR", "deadline": "2026-08-22"},
    {"owner": "Bob", "description": "Update docs", "deadline": ""},
]


# ── Markdown output ────────────────────────────────────────────────────────────

def test_writes_tasks_md(tmp_path):
    tw = TaskWriter()
    results = tw.write(SAMPLE_ITEMS, output_dir=tmp_path, meeting_name="standup")

    assert "markdown" in results
    tasks_file = Path(results["markdown"])
    assert tasks_file.exists()


def test_markdown_contains_yaml_frontmatter(tmp_path):
    tw = TaskWriter()
    tw.write(SAMPLE_ITEMS, output_dir=tmp_path, meeting_name="standup")
    content = (tmp_path / "tasks.md").read_text()

    assert "---" in content
    assert 'meeting: "standup"' in content
    assert "total_tasks: 2" in content


def test_markdown_checkboxes(tmp_path):
    tw = TaskWriter()
    tw.write(SAMPLE_ITEMS, output_dir=tmp_path, meeting_name="standup")
    content = (tmp_path / "tasks.md").read_text()

    assert "- [ ] **Alice**" in content
    assert "Review the PR" in content
    assert "by 2026-08-22" in content


def test_markdown_no_deadline_omits_by_clause(tmp_path):
    tw = TaskWriter()
    tw.write(SAMPLE_ITEMS, output_dir=tmp_path, meeting_name="standup")
    content = (tmp_path / "tasks.md").read_text()

    assert "**Bob** — Update docs" in content
    assert "**Bob** — Update docs _(by" not in content


def test_empty_action_items_writes_placeholder(tmp_path):
    tw = TaskWriter()
    tw.write([], output_dir=tmp_path, meeting_name="empty-meeting")
    content = (tmp_path / "tasks.md").read_text()

    assert "_No action items identified._" in content


def test_creates_output_dir_if_missing(tmp_path):
    tw = TaskWriter()
    new_dir = tmp_path / "nested" / "session"
    tw.write(SAMPLE_ITEMS, output_dir=new_dir, meeting_name="test")
    assert (new_dir / "tasks.md").exists()


# ── Notion guard ───────────────────────────────────────────────────────────────

def test_notion_skipped_when_no_token(tmp_path):
    tw = TaskWriter()
    with patch("meet_assistant.core.task_writer.settings") as mock_settings:
        mock_settings.notion_token = ""
        mock_settings.notion_database_id = "some-id"
        result = tw._push_notion(SAMPLE_ITEMS, "standup")
    assert "Skipped" in result
    assert "NOTION_TOKEN" in result


def test_notion_skipped_when_no_database_id(tmp_path):
    tw = TaskWriter()
    with patch("meet_assistant.core.task_writer.settings") as mock_settings:
        mock_settings.notion_token = "secret-token"
        mock_settings.notion_database_id = ""
        result = tw._push_notion(SAMPLE_ITEMS, "standup")
    assert "Skipped" in result
    assert "DATABASE_ID" in result


def test_notion_push_succeeds_with_mock(tmp_path):
    tw = TaskWriter()
    mock_client = MagicMock()

    with patch("meet_assistant.core.task_writer.settings") as mock_settings, \
         patch("meet_assistant.core.task_writer.Client", return_value=mock_client):

        mock_settings.notion_token = "secret"
        mock_settings.notion_database_id = "db-123"
        result = tw._push_notion(SAMPLE_ITEMS, "standup")

    assert "2" in result
    assert mock_client.pages.create.call_count == 2


# ── GitHub guard ───────────────────────────────────────────────────────────────

def test_github_skipped_when_no_token(tmp_path):
    tw = TaskWriter()
    with patch("meet_assistant.core.task_writer.settings") as mock_settings:
        mock_settings.github_token = ""
        mock_settings.github_repo = "org/repo"
        result = tw._push_github(SAMPLE_ITEMS, "standup")
    assert "Skipped" in result
    assert "GITHUB_TOKEN" in result


def test_github_skipped_when_no_repo(tmp_path):
    tw = TaskWriter()
    with patch("meet_assistant.core.task_writer.settings") as mock_settings:
        mock_settings.github_token = "ghp_secret"
        mock_settings.github_repo = ""
        result = tw._push_github(SAMPLE_ITEMS, "standup")
    assert "Skipped" in result
    assert "GITHUB_REPO" in result


def test_github_push_succeeds_with_mock():
    tw = TaskWriter()
    mock_gh = MagicMock()
    mock_repo = MagicMock()
    mock_gh.get_repo.return_value = mock_repo

    with patch("meet_assistant.core.task_writer.settings") as mock_settings, \
         patch("meet_assistant.core.task_writer.Github", return_value=mock_gh):

        mock_settings.github_token = "ghp_secret"
        mock_settings.github_repo = "org/repo"
        result = tw._push_github(SAMPLE_ITEMS, "standup")

    assert "2" in result
    assert mock_repo.create_issue.call_count == 2


# ── Full write() integration ───────────────────────────────────────────────────

def test_write_returns_all_results(tmp_path):
    tw = TaskWriter()
    results = tw.write(SAMPLE_ITEMS, output_dir=tmp_path, meeting_name="test",
                       push_to_notion=False, push_to_github=False)
    assert "markdown" in results
    assert "notion" not in results
    assert "github" not in results
