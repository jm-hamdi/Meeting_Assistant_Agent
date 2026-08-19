"""Custom exception hierarchy for Meeting Assistant."""

from __future__ import annotations


class MeetAssistError(Exception):
    """Base exception for all Meeting Assistant errors."""


class AudioCaptureError(MeetAssistError):
    """Raised when audio capture fails (device not found, stream error, etc.)."""


class TranscriptionError(MeetAssistError):
    """Raised when faster-whisper transcription fails."""


class SummarizationError(MeetAssistError):
    """Raised when the LLM summarization call fails or returns unparseable output."""


class TaskWriterError(MeetAssistError):
    """Raised when writing tasks to markdown, Notion, or GitHub fails."""


class ConfigurationError(MeetAssistError):
    """Raised when required configuration is missing or invalid."""
