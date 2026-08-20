"""Tests for MeetAssistSettings — defaults, env overrides, and validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from meet_assistant.settings import MeetAssistSettings


def test_default_lm_studio_url():
    s = MeetAssistSettings()
    assert s.lm_studio_base_url == "http://127.0.0.1:1234/v1"


def test_default_whisper_model():
    s = MeetAssistSettings()
    assert s.whisper_model_size == "small.en"


def test_default_audio_device():
    s = MeetAssistSettings()
    assert s.audio_device_name == "BlackHole 2ch"


def test_default_fallback_to_mic_is_true():
    s = MeetAssistSettings()
    assert s.audio_fallback_to_mic is True


def test_default_notion_token_is_empty():
    s = MeetAssistSettings()
    assert s.notion_token == ""


def test_default_github_token_is_empty():
    s = MeetAssistSettings()
    assert s.github_token == ""


def test_notion_disabled_when_token_empty():
    s = MeetAssistSettings()
    assert not s.notion_token  # falsy = disabled


def test_github_disabled_when_token_empty():
    s = MeetAssistSettings()
    assert not s.github_token  # falsy = disabled


def test_verbosity_bounds():
    s = MeetAssistSettings(verbosity=0)
    assert s.verbosity == 0
    s = MeetAssistSettings(verbosity=2)
    assert s.verbosity == 2


def test_verbosity_rejects_out_of_range():
    with pytest.raises(ValidationError):
        MeetAssistSettings(verbosity=5)


def test_max_agent_steps_minimum():
    with pytest.raises(ValidationError):
        MeetAssistSettings(max_agent_steps=0)


def test_env_override(monkeypatch):
    monkeypatch.setenv("MEETASSIST_WHISPER_MODEL_SIZE", "medium.en")
    monkeypatch.setenv("MEETASSIST_VERBOSITY", "2")
    s = MeetAssistSettings()
    assert s.whisper_model_size == "medium.en"
    assert s.verbosity == 2


def test_env_override_audio_device(monkeypatch):
    monkeypatch.setenv("MEETASSIST_AUDIO_DEVICE_NAME", "BlackHole 16ch")
    s = MeetAssistSettings()
    assert s.audio_device_name == "BlackHole 16ch"


def test_env_override_notion_token(monkeypatch):
    monkeypatch.setenv("MEETASSIST_NOTION_TOKEN", "secret-token")
    s = MeetAssistSettings()
    assert s.notion_token == "secret-token"


def test_output_dir_default():
    s = MeetAssistSettings()
    assert s.output_dir == "outputs"


def test_system_prompt_not_empty():
    s = MeetAssistSettings()
    assert len(s.system_prompt) > 0
    assert "run_full_pipeline" in s.system_prompt
