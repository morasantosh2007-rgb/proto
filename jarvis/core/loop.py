"""Main execution loop coordinating audio, brain, tools, safety, and TTS."""

import asyncio
import logging
import sys
import threading
import time
from typing import Optional

from jarvis.config import config
from jarvis.core.state import JarvisState, EventType, JarvisEvent
from jarvis.core.state_machine import StateMachine
from jarvis.core.event_bus import bus
from jarvis.audio.mic import MicrophoneStream
from jarvis.audio.vad import VoiceActivityDetector
from jarvis.audio.wake_word import WakeWordDetector
from jarvis.audio.stt import SpeechToText
from jarvis.audio.tts import TextToSpeech
from jarvis.audio.barge_in import BargeInController
from jarvis.brain.context import ConversationContext
from jarvis.brain.llm_interface import HybridBrain, BrainDecision
from jarvis.brain.router import ToolRouter
from jarvis.safety.tiers import SecurityPolicy, PermissionTier
from jarvis.safety.confirmation import confirmation_engine
from jarvis.safety.audit import audit_logger

logger = logging.getLogger("jarvis.core.loop")


class JarvisLoop:
    """The central runtime event loop of JARVIS."""

    def __init__(self, text_mode: bool = False, dry_run: bool = False):
        self.text_mode = text_mode
        self.dry_run = dry_run
        self.state_machine = StateMachine(follow_up_window_seconds=config.follow_up_window)
        self.context = ConversationContext()
        self.brain = HybridBrain(self.context)
        self.router = ToolRouter(dry_run=self.dry_run)

        # Audio subsystems
        self.vad = VoiceActivityDetector(energy_threshold=config.get("audio.energy_threshold", 300.0))
        self.wake_detector = WakeWordDetector(wake_word=config.wake_word, sensitivity=config.get("system.sensitivity", 0.5))
        self.stt = SpeechToText(
            model_size=config.whisper_model,
            device=config.whisper_device,
        )
        self.tts = TextToSpeech(
            voice=config.tts_voice,
            rate=config.tts_rate,
            pitch=config.tts_pitch,
        )
        self.barge_in = BargeInController(self.vad, on_interrupt=self._handle_barge_in)
        self.mic = MicrophoneStream(sample_rate=config.get("audio.sample_rate", 16000))

        self._running = False
        self._setup_event_listeners()

    def _setup_event_listeners(self) -> None:
        self.state_machine.add_listener(self._on_state_change)

    def _on_state_change(self, old_state: JarvisState, new_state: JarvisState) -> None:
        if new_state == JarvisState.SPEAKING:
            if config.get("system.barge_in", True) and not self.text_mode:
                self.barge_in.start_monitoring()
        else:
            self.barge_in.stop_monitoring()

    def _handle_barge_in(self, reason: str) -> None:
        self.tts.interrupt()
        self.state_machine.interrupt(reason=reason)

    def start(self) -> None:
        self._running = True
        logger.info(f"JARVIS initialized (TextMode={self.text_mode}, DryRun={self.dry_run}).")

        # Initial startup greeting
        greeting = f"All systems operational, {config.address_as}. Standing by."
        print(f"\n[JARVIS]: {greeting}\n")
        if not self.text_mode:
            self.tts.speak(greeting, dry_run=self.dry_run)

        if self.text_mode:
            self._run_text_mode()
        else:
            self._run_voice_loop()

    def _run_text_mode(self) -> None:
        """Interactive terminal text mode."""
        print(f"JARVIS Interactive Text Mode. Type your command, or 'exit'/'quit' to stop.\n")
        while self._running:
            try:
                user_input = input(f"{config.user_name} > ").strip()
                if not user_input:
                    continue
                if user_input.lower() in ["exit", "quit", "shutdown"]:
                    print(f"Powering down. Have a good day, {config.address_as}.")
                    break

                self.handle_user_utterance(user_input)
            except (KeyboardInterrupt, EOFError):
                break
        self.stop()

    def _run_voice_loop(self) -> None:
        """Main microphone and acoustic listening loop."""
        self.mic.start()
        audio_buffer = bytearray()
        silent_chunks = 0
        is_recording_speech = False

        try:
            while self._running:
                chunk = self.mic.read_chunk(timeout=0.1)
                if not chunk:
                    continue

                curr_state = self.state_machine.current_state

                # If speaking, check barge-in
                if curr_state == JarvisState.SPEAKING:
                    self.barge_in.process_audio_chunk(chunk)
                    continue

                # In IDLE state, monitor for wake word
                if curr_state == JarvisState.IDLE:
                    if self.wake_detector.process_frame(chunk):
                        logger.info("Wake word spotted via acoustic frame!")
                        self.state_machine.transition_to(JarvisState.LISTENING, "wake word detected")
                        self.tts.speak(f"Yes, {config.address_as}?", dry_run=self.dry_run)
                        audio_buffer.clear()
                        is_recording_speech = True
                        silent_chunks = 0
                    continue

                # In LISTENING state (either after wake word, follow-up window, or confirmation)
                if curr_state in [JarvisState.LISTENING, JarvisState.WAITING_CONFIRMATION]:
                    is_voice = self.vad.is_speech(chunk)
                    if is_voice:
                        is_recording_speech = True
                        audio_buffer.extend(chunk)
                        silent_chunks = 0
                    elif is_recording_speech:
                        audio_buffer.extend(chunk)
                        silent_chunks += 1
                        # 1.2s of silence indicates end of utterance
                        if silent_chunks > 12:
                            is_recording_speech = False
                            # Transcribe utterance
                            utterance = self.stt.transcribe(bytes(audio_buffer)).strip()
                            audio_buffer.clear()
                            silent_chunks = 0
                            if utterance:
                                self.handle_user_utterance(utterance)
        finally:
            self.mic.stop()

    def handle_user_utterance(self, utterance: str) -> None:
        """Process transcribed speech or text input through safety and brain."""
        logger.info(f"User utterance received: '{utterance}'")
        self.context.add_user_message(utterance)

        # 1. Check if we are waiting for voice confirmation
        if confirmation_engine.has_pending:
            confirmed, pending = confirmation_engine.evaluate_response(utterance)
            if confirmed and pending:
                self.state_machine.transition_to(JarvisState.ACTING, "user confirmed action")
                reply = f"Authorization confirmed, {config.address_as}. Executing {pending.tool_name} now."
                print(f"[JARVIS]: {reply}")
                self.tts.speak(reply, dry_run=self.dry_run)

                # Execute confirmed action
                results = self.router.execute_calls([{"name": pending.tool_name, "parameters": pending.parameters}])
                exec_msg = results[0].message if results else "Action complete."
                print(f"[JARVIS]: {exec_msg}")
                self.tts.speak(exec_msg, dry_run=self.dry_run)
                self.state_machine.on_speech_ended()
                return
            elif not confirmed and not confirmation_engine.has_pending:
                reply = f"Understood, {config.address_as}. Action cancelled."
                print(f"[JARVIS]: {reply}")
                self.tts.speak(reply, dry_run=self.dry_run)
                self.state_machine.on_speech_ended()
                return

        # 2. Check for manual setup wizard invocation
        if "connect my email" in utterance.lower() or "connect my calendar" in utterance.lower():
            reply = "Launching the integrations setup wizard, sir."
            print(f"[JARVIS]: {reply}")
            self.tts.speak(reply, dry_run=self.dry_run)
            from jarvis.integrations.setup_wizard import run_setup_wizard
            run_setup_wizard()
            return

        # 3. Brain planning
        self.state_machine.transition_to(JarvisState.THINKING, "processing request")
        decision = self.brain.process(utterance)

        # 4. Check if confirmation is required
        if decision.requires_confirmation:
            self.state_machine.transition_to(JarvisState.WAITING_CONFIRMATION, "awaiting approval")
            tool_call = decision.tool_calls[0]
            tier = SecurityPolicy.get_tier_for_action(tool_call.get("name", ""))
            confirmation_engine.request_confirmation(
                tool_call.get("name", ""),
                tool_call.get("parameters", {}),
                tier,
                decision.confirmation_prompt,
            )
            print(f"[JARVIS]: {decision.confirmation_prompt}")
            self.tts.speak(decision.confirmation_prompt, dry_run=self.dry_run)
            return

        # 5. Execute tool calls if any
        if decision.has_tools():
            self.state_machine.transition_to(JarvisState.ACTING, "executing tools")
            results = self.router.execute_calls(decision.tool_calls)
            self.state_machine.transition_to(JarvisState.SPEAKING, "reporting results")

            # Combine spoken response with verified tool results
            tool_summaries = [r.to_speech_summary() for r in results if r.message]
            full_reply = " ".join(tool_summaries)
            if not full_reply:
                full_reply = decision.spoken_response or f"Action completed, {config.address_as}."

            print(f"[JARVIS]: {full_reply}")
            self.context.add_assistant_message(full_reply)
            self.tts.speak(full_reply, dry_run=self.dry_run)
        else:
            # Conversational spoken response
            self.state_machine.transition_to(JarvisState.SPEAKING, "answering user")
            print(f"[JARVIS]: {decision.spoken_response}")
            self.context.add_assistant_message(decision.spoken_response)
            self.tts.speak(decision.spoken_response, dry_run=self.dry_run)

        # Transition to follow-up listening window
        self.state_machine.on_speech_ended()

    def stop(self) -> None:
        self._running = False
        self.state_machine.transition_to(JarvisState.SHUTDOWN, "user exit")
        self.mic.stop()
        self.tts.interrupt()
        logger.info("JARVIS shut down successfully.")
