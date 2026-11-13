"""Barge-in interruption handler."""

import logging
import threading
import time
from typing import Callable, Optional
from jarvis.audio.vad import VoiceActivityDetector
from jarvis.core.state import JarvisState, EventType, JarvisEvent
from jarvis.core.event_bus import bus

logger = logging.getLogger("jarvis.audio.barge_in")


class BargeInController:
    """Monitors incoming mic audio while JARVIS is speaking to trigger instant interruption."""

    def __init__(self, vad: VoiceActivityDetector, on_interrupt: Callable[[str], None]):
        self.vad = vad
        self.on_interrupt = on_interrupt
        self._active = False
        self._consecutive_speech_chunks = 0
        self._required_consecutive_chunks = 2  # ~100-200ms of sustained speech to avoid false clicks

    def start_monitoring(self) -> None:
        self._active = True
        self._consecutive_speech_chunks = 0

    def stop_monitoring(self) -> None:
        self._active = False
        self._consecutive_speech_chunks = 0

    def process_audio_chunk(self, chunk: bytes) -> bool:
        """Process incoming mic chunk during speech output. Returns True if interrupted."""
        if not self._active:
            return False

        if self.vad.is_speech(chunk):
            self._consecutive_speech_chunks += 1
            if self._consecutive_speech_chunks >= self._required_consecutive_chunks:
                logger.info("Barge-in speech activity detected!")
                self.stop_monitoring()
                bus.publish(JarvisEvent(EventType.BARGE_IN_TRIGGERED, {"reason": "voice_activity"}))
                self.on_interrupt("voice_activity")
                return True
        else:
            self._consecutive_speech_chunks = max(0, self._consecutive_speech_chunks - 1)

        return False
