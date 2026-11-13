"""High-fidelity Text-To-Speech (TTS) module with sounddevice in-memory playback and barge-in."""

import asyncio
import io
import logging
import os
import re
import subprocess
import threading
import time
from typing import List, Optional
import numpy as np

from jarvis.core.state import EventType, JarvisEvent
from jarvis.core.event_bus import bus

logger = logging.getLogger("jarvis.audio.tts")


class TextToSpeech:
    """Multi-engine streaming TTS with in-memory decoding and instant barge-in."""

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
        """Immediately halts any active audio playback (barge-in)."""
        logger.info("TTS interrupt invoked.")
        self._interrupt_event.set()
        try:
            import sounddevice as sd
            sd.stop()
        except Exception:
            pass

        with self._lock:
            if self._speaking_process and self._speaking_process.poll() is None:
                try:
                    self._speaking_process.terminate()
                except Exception:
                    pass
                self._speaking_process = None
            self._is_speaking = False

    def speak(self, text: str, dry_run: bool = False) -> None:
        """Speak text aloud, splitting sentences for natural conversational cadence."""
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
                    logger.info("TTS playback aborted mid-speech.")
                    break
                self._speak_sentence(sentence)
        finally:
            with self._lock:
                self._is_speaking = False
            bus.publish(JarvisEvent(EventType.SPEAK_ENDED, {"text": text}))

    def _split_sentences(self, text: str) -> List[str]:
        # Split by punctuation while keeping natural pauses
        parts = re.split(r'(?<=[.!?]) +', text.strip())
        return [p.strip() for p in parts if p.strip()]

    def _speak_sentence(self, sentence: str) -> None:
        if self._interrupt_event.is_set():
            return

        # Attempt 1: Edge-TTS
        if self.engine == "edge-tts":
            try:
                if self._synth_and_play_edge(sentence):
                    return
            except Exception as e:
                logger.debug(f"Edge-TTS failed ({e}), falling back to gTTS.")

        # Attempt 2: gTTS (Google Neural Voice) with in-memory playback
        try:
            if self._synth_and_play_gtts(sentence):
                return
        except Exception as e:
            logger.debug(f"gTTS failed ({e}), falling back to Windows SAPI.")

        # Attempt 3: Windows SAPI (System.Speech - 100% offline native)
        try:
            self._speak_with_sapi(sentence)
        except Exception as e:
            logger.error(f"All speech synthesizers failed for '{sentence}': {e}")

    def _play_audio_bytes(self, audio_bytes: bytes) -> bool:
        """Decode audio stream (MP3/WAV) in memory via PyAV and play through sounddevice."""
        if self._interrupt_event.is_set() or not audio_bytes:
            return False

        try:
            import av
            import sounddevice as sd

            buf = io.BytesIO(audio_bytes)
            container = av.open(buf)
            frames = []
            for frame in container.decode(audio=0):
                frames.append(frame.to_ndarray())

            if not frames:
                return False

            audio_data = np.concatenate(frames, axis=1)
            sr = container.streams.audio[0].rate

            # Audio data shape formatting
            if audio_data.ndim == 2:
                # Transpose from (channels, samples) to (samples, channels)
                audio_data = audio_data.T

            # Normalize to float32
            if audio_data.dtype == np.int16:
                audio_float = audio_data.astype(np.float32) / 32768.0
            elif audio_data.dtype == np.int32:
                audio_float = audio_data.astype(np.float32) / 2147483648.0
            else:
                audio_float = audio_data.astype(np.float32)

            duration = len(audio_float) / sr
            sd.play(audio_float, sr)

            # Wait while checking for interruption
            start_t = time.time()
            while time.time() - start_t < duration:
                if self._interrupt_event.is_set():
                    sd.stop()
                    return False
                time.sleep(0.05)

            sd.stop()
            return True
        except Exception as e:
            logger.error(f"Audio memory playback error: {e}")
            return False

    def _synth_and_play_edge(self, sentence: str) -> bool:
        """Synthesize using Edge-TTS into memory buffer."""
        import edge_tts

        audio_chunks = []

        async def _run_stream():
            communicate = edge_tts.Communicate(
                sentence,
                self.voice,
                rate=self.rate,
                volume=self.volume,
                pitch=self.pitch,
            )
            async for chunk in communicate.stream():
                if self._interrupt_event.is_set():
                    break
                if chunk["type"] == "audio":
                    audio_chunks.append(chunk["data"])

        try:
            asyncio.run(_run_stream())
            if audio_chunks:
                full_bytes = b"".join(audio_chunks)
                return self._play_audio_bytes(full_bytes)
        except Exception as e:
            logger.debug(f"Edge-TTS stream error: {e}")
        return False

    def _synth_and_play_gtts(self, sentence: str) -> bool:
        """Synthesize using gTTS into memory buffer and play."""
        from gtts import gTTS
        try:
            tts = gTTS(text=sentence, lang="en", tld="co.uk")
            buf = io.BytesIO()
            tts.write_to_fp(buf)
            buf.seek(0)
            return self._play_audio_bytes(buf.read())
        except Exception as e:
            logger.debug(f"gTTS error: {e}")
            return False

    def _speak_with_sapi(self, sentence: str) -> bool:
        """Offline speech fallback using Windows native System.Speech."""
        if self._interrupt_event.is_set():
            return False

        clean_text = sentence.replace("'", "''").replace('"', '`"')
        ps_cmd = (
            f"[System.Reflection.Assembly]::LoadWithPartialName('System.Speech') | Out-Null; "
            f"$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            f"$s.Speak('{clean_text}')"
        )
        try:
            self._speaking_process = subprocess.Popen(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            # Wait with strict timeout so it never hangs
            start_t = time.time()
            max_duration = max(5.0, len(sentence) * 0.15)
            while self._speaking_process.poll() is None:
                if self._interrupt_event.is_set() or (time.time() - start_t > max_duration):
                    self._speaking_process.terminate()
                    break
                time.sleep(0.05)

            return True
        except Exception as e:
            logger.error(f"SAPI error: {e}")
            return False
