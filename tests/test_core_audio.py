"""Tests for Core and Audio subsystems."""

import pytest
import time
from jarvis.core.state import JarvisState, EventType, JarvisEvent
from jarvis.core.state_machine import StateMachine
from jarvis.core.event_bus import EventBus
from jarvis.audio.vad import VoiceActivityDetector
from jarvis.audio.wake_word import WakeWordDetector
from jarvis.audio.tts import TextToSpeech
from jarvis.audio.barge_in import BargeInController


def test_state_machine_transitions():
    sm = StateMachine(follow_up_window_seconds=1.0)
    assert sm.current_state == JarvisState.IDLE

    # Valid transition IDLE -> LISTENING
    assert sm.transition_to(JarvisState.LISTENING) is True
    assert sm.current_state == JarvisState.LISTENING

    # Valid transition LISTENING -> THINKING
    assert sm.transition_to(JarvisState.THINKING) is True
    assert sm.current_state == JarvisState.THINKING

    # Valid transition THINKING -> ACTING
    assert sm.transition_to(JarvisState.ACTING) is True
    assert sm.current_state == JarvisState.ACTING

    # Valid transition ACTING -> SPEAKING
    assert sm.transition_to(JarvisState.SPEAKING) is True
    assert sm.current_state == JarvisState.SPEAKING

    # Invalid transition directly from SPEAKING to ACTING
    assert sm.transition_to(JarvisState.ACTING) is False


def test_state_machine_follow_up_and_interrupt():
    sm = StateMachine(follow_up_window_seconds=0.3)
    sm.transition_to(JarvisState.LISTENING)
    sm.transition_to(JarvisState.THINKING)
    sm.transition_to(JarvisState.SPEAKING)

    # When speech finishes, it opens follow-up window (moves to LISTENING)
    sm.on_speech_ended()
    assert sm.current_state == JarvisState.LISTENING

    # Wait for follow-up timer to expire
    time.sleep(0.4)
    assert sm.current_state == JarvisState.IDLE

    # Test barge-in interrupt
    sm.transition_to(JarvisState.LISTENING)
    sm.transition_to(JarvisState.THINKING)
    sm.transition_to(JarvisState.SPEAKING)
    sm.interrupt("User started speaking")
    assert sm.current_state == JarvisState.LISTENING


def test_event_bus_pub_sub():
    bus = EventBus()
    received = []

    def on_event(ev: JarvisEvent):
        received.append(ev)

    bus.subscribe(EventType.WAKE_WORD_DETECTED, on_event)
    bus.publish(JarvisEvent(EventType.WAKE_WORD_DETECTED, {"keyword": "jarvis"}))

    assert len(received) == 1
    assert received[0].payload["keyword"] == "jarvis"


def test_vad_and_wake_word_helpers():
    vad = VoiceActivityDetector(energy_threshold=100.0)
    # Silence (all zeros)
    silence = b"\x00" * 3200
    assert bool(vad.is_speech(silence)) is False

    detector = WakeWordDetector(wake_word="jarvis")
    assert detector.check_text_for_wake_word("Hey Jarvis what is the weather?") is True
    assert detector.check_text_for_wake_word("Jarvis open chrome") is True
    assert detector.check_text_for_wake_word("Good morning world") is False


def test_tts_dry_run():
    tts = TextToSpeech()
    # Dry run should execute without error
    tts.speak("Good morning, sir. All systems nominal.", dry_run=True)
    assert tts.is_speaking is False


def test_barge_in_controller():
    interrupted = []

    def on_intr(reason):
        interrupted.append(reason)

    vad = VoiceActivityDetector()
    ctrl = BargeInController(vad, on_intr)
    ctrl.start_monitoring()

    # Feeding empty/silence
    assert ctrl.process_audio_chunk(b"\x00" * 3200) is False
    assert len(interrupted) == 0
