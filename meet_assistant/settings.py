"""Typed application settings — all config lives here.

Override any value via environment variables prefixed with ``MEETASSIST_``
or via a ``.env`` file in the project root.
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class MeetAssistSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="MEETASSIST_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── LM Studio ─────────────────────────────────────────────────────────────
    lm_studio_base_url: str = Field(
        default="http://127.0.0.1:1234/v1",
        description="OpenAI-compatible API base URL served by LM Studio.",
    )
    lm_studio_api_key: str = Field(
        default="lm-studio",
        description="API key (LM Studio ignores this, but the SDK requires it).",
    )
    lm_studio_model_id: str = Field(
        default="openai/lmstudio-community/meta-llama-3.1-8b-instruct",
        description="LiteLLM model identifier. 'openai/' prefix selects the OpenAI-compat provider.",
    )

    # ── Whisper ───────────────────────────────────────────────────────────────
    whisper_model_size: str = Field(
        default="small.en",
        description="Whisper model size: tiny.en / base.en / small.en / medium.en / large-v3",
    )
    whisper_device: str = Field(
        default="auto",
        description="Compute device: 'cpu', 'cuda', or 'auto'.",
    )
    whisper_compute_type: str = Field(
        default="int8",
        description="Quantisation: 'int8' for CPU (Apple Silicon safe), 'float16' for GPU.",
    )

    # ── Audio Capture ─────────────────────────────────────────────────────────
    audio_device_name: str = Field(
        default="BlackHole 2ch",
        description="Name of the loopback audio input device.",
    )
    audio_fallback_to_mic: bool = Field(
        default=True,
        description="Fall back to system microphone if BlackHole is not found.",
    )
    audio_sample_rate: int = Field(
        default=16000,
        description="Recording sample rate in Hz. Whisper natively uses 16000.",
    )
    audio_channels: int = Field(
        default=1,
        description="Number of audio channels. Mono (1) is sufficient for speech.",
    )

    # ── Output ────────────────────────────────────────────────────────────────
    output_dir: str = Field(
        default="outputs",
        description="Root directory where meeting session folders are saved.",
    )

    # ── Agent ─────────────────────────────────────────────────────────────────
    max_agent_steps: int = Field(
        default=15,
        ge=1,
        description="Hard ceiling on ReAct iterations per user request.",
    )
    verbosity: int = Field(
        default=1,
        ge=0,
        le=2,
        description="Logging verbosity: 0 = WARNING, 1 = INFO, 2 = DEBUG.",
    )

    # ── Notion (optional) ─────────────────────────────────────────────────────
    notion_token: str = Field(
        default="",
        description="Notion integration token. Leave empty to disable Notion output.",
    )
    notion_database_id: str = Field(
        default="",
        description="Notion database ID where tasks are created.",
    )

    # ── GitHub (optional) ─────────────────────────────────────────────────────
    github_token: str = Field(
        default="",
        description="GitHub personal access token. Leave empty to disable GitHub Issues.",
    )
    github_repo: str = Field(
        default="",
        description="GitHub repository in 'owner/repo' format.",
    )

    # ── System Prompt ─────────────────────────────────────────────────────────
    system_prompt: str = Field(
        default="""\
You are **Meet Assistant**, an AI that helps manage meetings.
You can record audio, transcribe speech to text, summarize transcripts, and create follow-up tasks.

## Available Tools
- `start_recording(meeting_name)` — begin capturing audio from BlackHole or microphone
- `stop_recording()` — stop capture and save WAV file
- `recording_status()` — check if recording is active and for how long
- `transcribe_audio(audio_path, language)` — convert WAV to text using local Whisper
- `summarize_transcript(transcript, meeting_name)` — extract summary + action items via LLM
- `create_tasks(action_items_json, output_dir, push_to_notion, push_to_github)` — write tasks
- `run_full_pipeline(duration_seconds, meeting_name)` — run everything end-to-end
- `list_meetings()` — show past meeting sessions
- `get_meeting(meeting_name)` — retrieve a specific past meeting

## Guidelines
- For a full meeting workflow, prefer `run_full_pipeline` over calling individual tools.
- Always confirm with the user before pushing tasks to Notion or GitHub.
- If the user provides an existing audio file, skip straight to `transcribe_audio`.
- Keep responses concise — report file paths and key takeaways, not the full transcript.
""",
    )


# ── Singleton ──────────────────────────────────────────────────────────────────
settings = MeetAssistSettings()
