"""Task writer — outputs action items to markdown, Notion, and/or GitHub Issues."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from meet_assistant.exceptions import TaskWriterError
from meet_assistant.settings import settings

logger = logging.getLogger("meet_assistant.core.task_writer")


class TaskWriter:
    """Writes action items to one or more destinations."""

    def write(
        self,
        action_items: list[dict],
        output_dir: str | Path,
        meeting_name: str = "",
        push_to_notion: bool = False,
        push_to_github: bool = False,
    ) -> dict[str, str]:
        """Write tasks to all requested destinations.

        Returns a dict of destination → result message.
        """
        results: dict[str, str] = {}
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        # Always write markdown
        md_path = self._write_markdown(action_items, out, meeting_name)
        results["markdown"] = str(md_path)

        if push_to_notion:
            results["notion"] = self._push_notion(action_items, meeting_name)

        if push_to_github:
            results["github"] = self._push_github(action_items, meeting_name)

        return results

    # ── Markdown ───────────────────────────────────────────────────────────────

    def _write_markdown(
        self, action_items: list[dict], output_dir: Path, meeting_name: str
    ) -> Path:
        path = output_dir / "tasks.md"
        now = datetime.now().isoformat(timespec="seconds")

        lines = [
            "---",
            f'meeting: "{meeting_name}"',
            f'generated: "{now}"',
            f"total_tasks: {len(action_items)}",
            "---",
            "",
            "## Action Items",
            "",
        ]

        if not action_items:
            lines.append("_No action items identified._")
        else:
            for item in action_items:
                owner = item.get("owner", "unknown")
                desc = item.get("description", "")
                deadline = item.get("deadline", "")
                deadline_str = f" _(by {deadline})_" if deadline else ""
                lines.append(f"- [ ] **{owner}** — {desc}{deadline_str}")

        path.write_text("\n".join(lines), encoding="utf-8")
        logger.info("Tasks saved → %s (%d items)", path, len(action_items))
        return path

    # ── Notion ─────────────────────────────────────────────────────────────────

    def _push_notion(self, action_items: list[dict], meeting_name: str) -> str:
        if not settings.notion_token:
            return "Skipped — MEETASSIST_NOTION_TOKEN is not set."
        if not settings.notion_database_id:
            return "Skipped — MEETASSIST_NOTION_DATABASE_ID is not set."

        try:
            from notion_client import Client
        except ImportError:
            return "Failed — notion-client is not installed. Run: pip install notion-client"

        try:
            client = Client(auth=settings.notion_token)
            created = 0
            for item in action_items:
                client.pages.create(
                    parent={"database_id": settings.notion_database_id},
                    properties={
                        "Name": {
                            "title": [{"text": {"content": item.get("description", "Task")}}]
                        },
                        "Owner": {
                            "rich_text": [{"text": {"content": item.get("owner", "unknown")}}]
                        },
                        "Meeting": {
                            "rich_text": [{"text": {"content": meeting_name}}]
                        },
                        "Deadline": {
                            "rich_text": [{"text": {"content": item.get("deadline", "")}}]
                        },
                    },
                )
                created += 1
            return f"Created {created} page(s) in Notion."
        except Exception as exc:
            logger.error("Notion push failed: %s", exc)
            return f"Failed — {exc}"

    # ── GitHub Issues ──────────────────────────────────────────────────────────

    def _push_github(self, action_items: list[dict], meeting_name: str) -> str:
        if not settings.github_token:
            return "Skipped — MEETASSIST_GITHUB_TOKEN is not set."
        if not settings.github_repo:
            return "Skipped — MEETASSIST_GITHUB_REPO is not set."

        try:
            from github import Github
        except ImportError:
            return "Failed — PyGithub is not installed. Run: pip install PyGithub"

        try:
            gh = Github(settings.github_token)
            repo = gh.get_repo(settings.github_repo)
            created = 0
            for item in action_items:
                owner = item.get("owner", "unknown")
                desc = item.get("description", "Task")
                deadline = item.get("deadline", "")
                body = f"**Meeting:** {meeting_name}\n**Owner:** {owner}"
                if deadline:
                    body += f"\n**Deadline:** {deadline}"
                repo.create_issue(title=desc, body=body, labels=["meeting-task"])
                created += 1
            return f"Created {created} GitHub Issue(s) in {settings.github_repo}."
        except Exception as exc:
            logger.error("GitHub push failed: %s", exc)
            return f"Failed — {exc}"


# ── Module-level singleton ─────────────────────────────────────────────────────
task_writer = TaskWriter()
