"""State representations and event types for JARVIS."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class JarvisState(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    ACTING = "acting"
    SPEAKING = "speaking"
    WAITING_CONFIRMATION = "waiting_confirmation"
    INTERRUPTED = "interrupted"
    SHUTDOWN = "shutdown"


class EventType(str, Enum):
    WAKE_WORD_DETECTED = "wake_word_detected"
    SPEECH_STARTED = "speech_started"
    SPEECH_ENDED = "speech_ended"
    TEXT_INPUT = "text_input"
    THOUGHT_GENERATED = "thought_generated"
    TOOL_CALL_REQUESTED = "tool_call_requested"
    TOOL_COMPLETED = "tool_completed"
    SPEAK_STARTED = "speak_started"
    SPEAK_ENDED = "speak_ended"
    BARGE_IN_TRIGGERED = "barge_in_triggered"
    CONFIRMATION_REQUESTED = "confirmation_requested"
    CONFIRMATION_RECEIVED = "confirmation_received"
    ERROR_OCCURRED = "error_occurred"


@dataclass
class JarvisEvent:
    event_type: EventType
    payload: Any = None
    source: str = "core"
    timestamp: datetime = field(default_factory=datetime.now)
