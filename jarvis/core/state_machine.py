"""State machine managing JARVIS lifecycle and state transitions."""

import logging
import threading
import time
from typing import Callable, List, Optional
from jarvis.core.state import JarvisState, JarvisEvent, EventType
from jarvis.core.event_bus import bus

logger = logging.getLogger("jarvis.core.state_machine")


class StateMachine:
    """Manages system state transitions, conversational windows, and interruption states."""

    ALLOWED_TRANSITIONS = {
        JarvisState.IDLE: [JarvisState.LISTENING, JarvisState.THINKING, JarvisState.SPEAKING, JarvisState.ACTING, JarvisState.SHUTDOWN],
        JarvisState.LISTENING: [JarvisState.THINKING, JarvisState.SPEAKING, JarvisState.IDLE, JarvisState.INTERRUPTED, JarvisState.SHUTDOWN],
        JarvisState.THINKING: [JarvisState.ACTING, JarvisState.SPEAKING, JarvisState.WAITING_CONFIRMATION, JarvisState.IDLE, JarvisState.SHUTDOWN],
        JarvisState.ACTING: [JarvisState.THINKING, JarvisState.SPEAKING, JarvisState.IDLE, JarvisState.SHUTDOWN],
        JarvisState.SPEAKING: [JarvisState.LISTENING, JarvisState.IDLE, JarvisState.INTERRUPTED, JarvisState.SHUTDOWN],
        JarvisState.WAITING_CONFIRMATION: [JarvisState.ACTING, JarvisState.SPEAKING, JarvisState.IDLE, JarvisState.SHUTDOWN],
        JarvisState.INTERRUPTED: [JarvisState.LISTENING, JarvisState.IDLE, JarvisState.SHUTDOWN],
        JarvisState.SHUTDOWN: [JarvisState.IDLE],
    }

    def __init__(self, follow_up_window_seconds: float = 8.0):
        self._current_state = JarvisState.IDLE
        self._lock = threading.Lock()
        self._follow_up_window = follow_up_window_seconds
        self._follow_up_timer: Optional[threading.Timer] = None
        self._listeners: List[Callable[[JarvisState, JarvisState], None]] = []

    @property
    def current_state(self) -> JarvisState:
        with self._lock:
            return self._current_state

    def add_listener(self, listener: Callable[[JarvisState, JarvisState], None]) -> None:
        self._listeners.append(listener)

    def transition_to(self, new_state: JarvisState, reason: str = "") -> bool:
        with self._lock:
            old_state = self._current_state
            if new_state == old_state:
                return True

            allowed = self.ALLOWED_TRANSITIONS.get(old_state, [])
            if new_state not in allowed:
                logger.warning(
                    f"Illegal state transition attempted: {old_state} -> {new_state} (Reason: {reason})"
                )
                return False

            self._cancel_follow_up_timer()
            self._current_state = new_state
            logger.info(f"State: {old_state.value} -> {new_state.value} [{reason}]")

            # Fire listeners
            for listener in self._listeners:
                try:
                    listener(old_state, new_state)
                except Exception as e:
                    logger.error(f"Listener error during state change: {e}")

            # If moving to SPEAKING, prepare for follow-up or idle transition after speech ends
            return True

    def on_speech_ended(self) -> None:
        """Called when TTS has finished speaking."""
        with self._lock:
            if self._current_state == JarvisState.SPEAKING:
                # Open follow-up conversation window
                self._current_state = JarvisState.LISTENING
                logger.info(
                    f"Follow-up window opened ({self._follow_up_window}s): Listening without wake word..."
                )
                self._cancel_follow_up_timer()
                self._follow_up_timer = threading.Timer(self._follow_up_window, self._on_follow_up_timeout)
                self._follow_up_timer.daemon = True
                self._follow_up_timer.start()

                for listener in self._listeners:
                    listener(JarvisState.SPEAKING, JarvisState.LISTENING)

    def _on_follow_up_timeout(self) -> None:
        with self._lock:
            if self._current_state == JarvisState.LISTENING:
                logger.info("Follow-up window expired: returning to IDLE.")
                old_state = self._current_state
                self._current_state = JarvisState.IDLE
                for listener in self._listeners:
                    listener(old_state, JarvisState.IDLE)

    def interrupt(self, reason: str = "barge-in") -> None:
        """Immediately trigger interrupt and transition to LISTENING."""
        with self._lock:
            self._cancel_follow_up_timer()
            old_state = self._current_state
            self._current_state = JarvisState.INTERRUPTED
            logger.warning(f"JARVIS interrupted: {old_state} -> INTERRUPTED ({reason})")
            for listener in self._listeners:
                listener(old_state, JarvisState.INTERRUPTED)

        # Transition directly from INTERRUPTED to LISTENING
        self.transition_to(JarvisState.LISTENING, "listening to interrupt input")

    def _cancel_follow_up_timer(self) -> None:
        if self._follow_up_timer:
            self._follow_up_timer.cancel()
            self._follow_up_timer = None
