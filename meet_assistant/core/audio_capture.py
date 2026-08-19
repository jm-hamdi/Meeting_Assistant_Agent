"""Audio capture — records system audio via BlackHole loopback or microphone fallback."""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import sounddevice as sd
import soundfile as sf

from meet_assistant.exceptions import AudioCaptureError
from meet_assistant.settings import settings

logger = logging.getLogger("meet_assistant.core.audio_capture")


@dataclass
class RecordingSession:
    meeting_name: str
    output_dir: Path
    device_name: str
    sample_rate: int
    started_at: float = field(default_factory=time.time)
    chunks: list[np.ndarray] = field(default_factory=list)
    audio_path: Path | None = None


def find_device(name: str) -> int | None:
    """Return the device index whose name contains *name* (case-insensitive) and has input channels."""
    for i, dev in enumerate(sd.query_devices()):
        if name.lower() in dev["name"].lower() and dev["max_input_channels"] > 0:
            return i
    return None


def get_device_sample_rate(device_index: int) -> int:
    """Return the default sample rate of a device."""
    dev = sd.query_devices(device_index)
    return int(dev["default_samplerate"])


class AudioCapture:
    """Records audio from BlackHole (or mic fallback) into a WAV file."""

    def __init__(self) -> None:
        self._session: RecordingSession | None = None
        self._stream: sd.InputStream | None = None
        self._lock = threading.Lock()

    # ── Public API ─────────────────────────────────────────────────────────────

    def start(self, meeting_name: str = "") -> RecordingSession:
        with self._lock:
            if self._session is not None:
                raise AudioCaptureError("A recording is already in progress. Call stop() first.")

            device_index, device_name = self._resolve_device()
            sample_rate = self._resolve_sample_rate(device_index)

            slug = meeting_name.strip() or datetime.now().strftime("%Y-%m-%d_%H-%M")
            output_dir = Path(settings.output_dir) / slug
            output_dir.mkdir(parents=True, exist_ok=True)

            session = RecordingSession(
                meeting_name=slug,
                output_dir=output_dir,
                device_name=device_name,
                sample_rate=sample_rate,
            )
            self._session = session

            self._stream = sd.InputStream(
                device=device_index,
                samplerate=sample_rate,
                channels=settings.audio_channels,
                dtype="float32",
                callback=self._callback,
            )
            self._stream.start()
            logger.info("Recording started — device: %s @ %d Hz → %s", device_name, sample_rate, output_dir)
            return session

    def stop(self) -> Path:
        with self._lock:
            if self._session is None or self._stream is None:
                raise AudioCaptureError("No active recording session.")

            self._stream.stop()
            self._stream.close()
            self._stream = None

            session = self._session
            self._session = None

        if not session.chunks:
            raise AudioCaptureError("Recording produced no audio data.")

        audio = np.concatenate(session.chunks, axis=0)
        audio_path = session.output_dir / "audio.wav"
        sf.write(str(audio_path), audio, session.sample_rate)

        duration = time.time() - session.started_at
        logger.info("Recording saved — %.1f s → %s", duration, audio_path)
        return audio_path

    def status(self) -> dict[str, Any]:
        with self._lock:
            if self._session is None:
                return {"active": False}
            elapsed = time.time() - self._session.started_at
            return {
                "active": True,
                "meeting_name": self._session.meeting_name,
                "device": self._session.device_name,
                "elapsed_seconds": round(elapsed, 1),
                "output_dir": str(self._session.output_dir),
            }

    @property
    def is_active(self) -> bool:
        return self._session is not None

    # ── Internal ───────────────────────────────────────────────────────────────

    def _callback(self, indata: np.ndarray, frames: int, time_info: Any, status: Any) -> None:
        if status:
            logger.warning("Audio stream status: %s", status)
        if self._session is not None:
            self._session.chunks.append(indata.copy())

    def _resolve_device(self) -> tuple[int | None, str]:
        """Return (device_index, device_name). Falls back to mic if BlackHole not found."""
        device_index = find_device(settings.audio_device_name)
        if device_index is not None:
            name = sd.query_devices(device_index)["name"]
            logger.info("Using loopback device: %s (index %d)", name, device_index)
            return device_index, name

        if not settings.audio_fallback_to_mic:
            raise AudioCaptureError(
                f"Audio device '{settings.audio_device_name}' not found and fallback is disabled. "
                f"Install BlackHole: brew install blackhole-2ch"
            )

        logger.warning(
            "'%s' not found — falling back to system microphone. "
            "Only your voice will be captured, not remote participants.",
            settings.audio_device_name,
        )
        # None = sounddevice default input device
        default = sd.query_devices(kind="input")
        return None, default["name"]

    def _resolve_sample_rate(self, device_index: int | None) -> int:
        """Use configured rate if the device supports it, otherwise use device native rate."""
        wanted = settings.audio_sample_rate
        if device_index is None:
            return wanted
        native = get_device_sample_rate(device_index)
        if native != wanted:
            logger.info(
                "Device native rate is %d Hz; capturing at %d Hz — faster-whisper will resample.",
                native, native,
            )
            return native
        return wanted


# ── Module-level singleton ─────────────────────────────────────────────────────
audio_capture = AudioCapture()
