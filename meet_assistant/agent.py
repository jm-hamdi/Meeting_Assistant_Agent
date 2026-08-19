"""Agent factory — builds the smolagents CodeAgent wired to LM Studio."""

from __future__ import annotations

import logging
import re
from typing import Sequence

from smolagents import CodeAgent, LiteLLMModel
from smolagents.tools import Tool

from meet_assistant.settings import settings
from meet_assistant.tools._registry import discover_tools

logger = logging.getLogger("meet_assistant.agent")

# ── Patch smolagents code parser for local LLM compatibility ──────────────────
# Local models sometimes emit non-standard code fence tags (```tool_code, ```code, etc.)
_CODE_BLOCK_ALIASES = re.compile(
    r"```(?:tool_code|code|tool|py|python|Tool_code|PYTHON)\b",
    re.IGNORECASE,
)


def _patch_code_parser() -> None:
    import smolagents.utils as _utils

    _original_parse = _utils.parse_code_blobs

    def _patched_parse(text: str, code_block_tags: tuple[str, str]) -> str:
        normalized = _CODE_BLOCK_ALIASES.sub("```python", text)
        return _original_parse(normalized, code_block_tags)

    _utils.parse_code_blobs = _patched_parse

    try:
        import smolagents.agents as _agents
        _agents.parse_code_blobs = _patched_parse
    except (ImportError, AttributeError):
        pass

    logger.debug("Patched smolagents code parser for local LLM compatibility")


_patch_code_parser()


def build_agent(
    custom_tools: Sequence[Tool] | None = None,
    model_id: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    max_steps: int | None = None,
) -> CodeAgent:
    """Build and return a configured CodeAgent for meeting assistance."""
    target_model_id = model_id or settings.lm_studio_model_id
    target_base_url = base_url or settings.lm_studio_base_url
    target_api_key = api_key or settings.lm_studio_api_key
    target_max_steps = max_steps or settings.max_agent_steps

    logger.info("Initialising LLM: %s @ %s", target_model_id, target_base_url)

    model = LiteLLMModel(
        model_id=target_model_id,
        api_base=target_base_url,
        api_key=target_api_key,
    )

    tools_to_use = list(custom_tools) if custom_tools is not None else discover_tools()
    logger.info("Agent loaded with %d tools: %s", len(tools_to_use), [t.name for t in tools_to_use])

    return CodeAgent(
        tools=tools_to_use,
        model=model,
        max_steps=target_max_steps,
        add_base_tools=False,
        system_prompt=settings.system_prompt,
    )
