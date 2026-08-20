"""Summarizer — sends transcript to local LLM and extracts structured meeting output."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from meet_assistant.exceptions import SummarizationError
from meet_assistant.settings import settings

logger = logging.getLogger("meet_assistant.core.summarizer")

_SYSTEM_PROMPT = """\
You are a meeting assistant that extracts structured information from transcripts.
Always respond with valid JSON only — no markdown fences, no explanation, just the JSON object.
"""

_USER_PROMPT = """\
Analyse this meeting transcript and return a JSON object with exactly these keys:

{
  "summary": ["bullet 1", "bullet 2", "bullet 3"],
  "decisions": ["decision 1", "decision 2"],
  "action_items": [
    {"owner": "name or unknown", "description": "what to do", "deadline": "date or ''"}
  ],
  "blockers": ["blocker 1"]
}

Rules:
- summary: 3-5 concise bullet points covering the main topics discussed
- decisions: concrete decisions made during the meeting (empty list if none)
- action_items: every task someone committed to; owner is a name or 'unknown'
- blockers: open questions or impediments raised (empty list if none)

TRANSCRIPT:
{transcript}
"""


@dataclass
class MeetingSummary:
    summary: list[str] = field(default_factory=list)
    decisions: list[str] = field(default_factory=list)
    action_items: list[dict] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    meeting_name: str = ""
    raw_response: str = ""

    def to_markdown(self) -> str:
        lines: list[str] = [f"# Meeting Summary — {self.meeting_name}\n"]

        lines.append("## Summary")
        for item in self.summary:
            lines.append(f"- {item}")

        if self.decisions:
            lines.append("\n## Key Decisions")
            for d in self.decisions:
                lines.append(f"- {d}")

        if self.action_items:
            lines.append("\n## Action Items")
            for ai in self.action_items:
                owner = ai.get("owner", "unknown")
                desc = ai.get("description", "")
                deadline = ai.get("deadline", "")
                deadline_str = f" _(by {deadline})_" if deadline else ""
                lines.append(f"- [ ] **{owner}** — {desc}{deadline_str}")

        if self.blockers:
            lines.append("\n## Blockers / Open Questions")
            for b in self.blockers:
                lines.append(f"- {b}")

        return "\n".join(lines)


class Summarizer:
    """Calls the local LLM to summarise a transcript and returns a MeetingSummary."""

    def summarise(self, transcript: str, meeting_name: str = "") -> MeetingSummary:
        if not transcript.strip():
            raise SummarizationError("Transcript is empty — nothing to summarise.")

        raw = self._call_llm(transcript)
        parsed = self._parse(raw)
        parsed.meeting_name = meeting_name
        parsed.raw_response = raw
        return parsed

    def summarise_and_save(self, transcript: str, output_dir: str | Path, meeting_name: str = "") -> Path:
        """Summarise and write summary.md to *output_dir*. Returns the file path."""
        summary = self.summarise(transcript, meeting_name)
        out = Path(output_dir) / "summary.md"
        out.write_text(summary.to_markdown(), encoding="utf-8")
        logger.info("Summary saved → %s", out)
        return out

    # ── Internal ───────────────────────────────────────────────────────────────

    def _call_llm(self, transcript: str) -> str:
        try:
            import litellm
        except ImportError as exc:
            raise SummarizationError("litellm is not installed. Run: pip install litellm") from exc

        prompt = _USER_PROMPT.format(transcript=transcript)

        try:
            response = litellm.completion(
                model=settings.lm_studio_model_id,
                api_base=settings.lm_studio_base_url,
                api_key=settings.lm_studio_api_key,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=1024,
            )
            return response.choices[0].message.content.strip()
        except Exception as exc:
            raise SummarizationError(f"LLM call failed: {exc}") from exc

    def _parse(self, raw: str) -> MeetingSummary:
        # Strip markdown fences if the model added them anyway
        text = raw.strip()
        if text.startswith("```"):
            text = "\n".join(text.splitlines()[1:])
        if text.endswith("```"):
            text = "\n".join(text.splitlines()[:-1])
        text = text.strip()

        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            logger.warning("LLM returned non-JSON — attempting partial extraction. Error: %s", exc)
            return self._fallback_parse(raw)

        return MeetingSummary(
            summary=_ensure_list(data.get("summary", [])),
            decisions=_ensure_list(data.get("decisions", [])),
            action_items=_ensure_action_items(data.get("action_items", [])),
            blockers=_ensure_list(data.get("blockers", [])),
        )

    def _fallback_parse(self, raw: str) -> MeetingSummary:
        """When JSON parsing fails, return the raw text as a single summary bullet."""
        logger.warning("Falling back to raw text summary.")
        return MeetingSummary(summary=[raw[:500]])


def _ensure_list(value) -> list[str]:
    if isinstance(value, list):
        return [str(v) for v in value]
    if isinstance(value, str):
        return [value]
    return []


def _ensure_action_items(value) -> list[dict]:
    if not isinstance(value, list):
        return []
    result = []
    for item in value:
        if isinstance(item, dict):
            result.append({
                "owner": str(item.get("owner", "unknown")),
                "description": str(item.get("description", "")),
                "deadline": str(item.get("deadline", "")),
            })
    return result


# ── Module-level singleton ─────────────────────────────────────────────────────
summarizer = Summarizer()
