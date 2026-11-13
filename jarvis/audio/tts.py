"""Text-To-Speech (TTS) module with streaming speech, multi-engine support, and barge-in."""

import asyncio
import logging
import os
import re
import subprocess
import tempfile
import threading
from typing import Optional, List
from jarvis.core.state import JarvisState, EventType, JarvisEvent
from jarvis.core.event_bus import bus

logger = logging.getLogger("jarvis.audio.tts")


class TextToSpeech:
    """Multi-engine streaming TTS supporting Edge-TTS, Windows SAPI, and gTTS."""

    def __init__(
        self,
        engine: str = "edge-tts",
        voice: str = "en-GB-RyanNeural",
        rate: str = "+0%",
        volume: str = "+0%",
        pitch: str = "+0Hz",
    ):
        self.engine = engine
        self.voice = voice
        self.rate = rate
        self.volume = volume
        self.pitch = pitch
        self._interrupt_event = threading.Event()
        self._speaking_process: Optional[subprocess.Popen] = None
        self._is_speaking = False
        self._lock = threading.Lock()

    @property
    def is_speaking(self) -> bool:
        with self._lock:
            return self._is_speaking

    def interrupt(self) -> None:
        """Immediately halts any current speech output (barge-in)."""
        logger.info("TTS interrupt triggered.")
        self._interrupt_event.set()
        with self._lock:
            if self._speaking_process and self._speaking_process.poll() is None:
                try:
                    self._speaking_process.terminate()
                except Exception:
                    pass
                self._speaking_process = None
            self._is_speaking = False

    def speak(self, text: str, dry_run: bool = False) -> None:
        """Synchronously speak text, splitting by sentences for streaming output."""
        if not text or not text.strip():
            return

        if dry_run:
            print(f"[JARVIS SPEECH (Dry-Run)]: {text}")
            return

        self._interrupt_event.clear()
        with self._lock:
            self._is_speaking = True

        bus.publish(JarvisEvent(EventType.SPEAK_STARTED, {"text": text}))

        try:
            sentences = self._split_sentences(text)
            for sentence in sentences:
                if self._interrupt_event.is_set():
                    logger.info("TTS aborted mid-stream due to interrupt.")
                    break
                self._speak_sentence(sentence)
        finally:
            with self._lock:
                self._is_speaking = False
            bus.publish(JarvisEvent(EventType.SPEAK_ENDED, {"text": text}))

    def _split_sentences(self, text: str) -> List[str]:
        # Split by punctuation while keeping natural conversational cadence
        parts = re.split(r'(?<=[.!?]) +', text.strip())
        return [p.strip() for p in parts if p.strip()]

    def _speak_sentence(self, sentence: str) -> None:
        if self._interrupt_event.is_set():
            return

        # Attempt primary engine first, then fall back to Windows SAPI
        spoken = False
        if self.engine == "edge-tts":
            try:
                spoken = self._speak_with_edge_tts(sentence)
            except Exception as e:
                logger.debug(f"Edge-TTS failed ({e}), falling back to Windows SAPI.")

        if not spoken:
            try:
                spoken = self._speak_with_sapi(sentence)
            except Exception as e:
                logger.error(f"Windows SAPI failed ({e}), falling back to gTTS.")

        if not spoken:
            try:
                self._speak_with_gtts(sentence)
            except Exception as e:
                logger.error(f"All TTS engines failed for sentence: '{sentence}': {e}")

    def _speak_with_edge_tts(self, sentence: str) -> bool:
        """Synthesize with Edge-TTS and play."""
        import edge_tts
        temp_file = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        temp_path = temp_file.name
        temp_file.close()

        async def _synth():
            communicate = edge_tts.Communicate(
                sentence,
                self.voice,
                rate=self.rate,
                volume=self.volume,
                pitch=self.pitch,
            )
            await communicate.save(temp_path)

        try:
            asyncio.run(_synth())
            self._play_audio_file(temp_path)
            return True
        finally:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass

    def _speak_with_sapi(self, sentence: str) -> bool:
        """Use Windows native System.Speech via PowerShell (instant & offline)."""
        if self._interrupt_event.is_set():
            return False

        clean_text = sentence.replace("'", "''").replace('"', '`"')
        # PowerShell command calling .NET SpeechSynthesizer
        ps_cmd = (
            f"Add-Type -AssemblyName System.Speech; "
            f"$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            f"$s.Speak('{clean_text}')"
        )
        self._speaking_process = subprocess.Popen(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        while self._speaking_process.poll() is None:
            if self._interrupt_event.is_set():
                self._speaking_process.terminate()
                return False
            self._interrupt_event.wait(0.05)

        return self._speaking_process.returncode == 0

    def _speak_with_gtts(self, sentence: str) -> bool:
        """Synthesize using Google TTS and play."""
        from gtts import gTTS
        temp_file = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        temp_path = temp_file.name
        temp_file.close()

        try:
            tts = gTTS(text=sentence, lang="en", tld="co.uk")
            tts.save(temp_path)
            self._play_audio_file(temp_path)
            return True
        finally:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass

    def _play_audio_file(self, file_path: str) -> None:
        """Play audio file with barge-in support."""
        if self._interrupt_event.is_set():
            return

        # Use Windows Media Player or PowerShell to play mp3
        ps_script = (
            f"$wmp = New-Object -ComObject WMPlayer.OCX; "
            f"$wmp.URL = '{file_path}'; "
            f"$wmp.controls.play(); "
            f"while ($wmp.playState -ne 1 -and $wmp.playState -ne 0) {{ Start-Sleep -Milliseconds 100 }}"
        )
        self._speaking_process = subprocess.Popen(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        while self._speaking_process.poll() is None:
            if self._interrupt_event.is_set():
                self._speaking_process.terminate()
                break
            self._interrupt_event.wait(0.05)
