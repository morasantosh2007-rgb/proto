"""Speech-To-Text (STT) implementation using faster-whisper with graceful fallback."""

import io
import os
import wave
import logging
from typing import Optional
import numpy as np

logger = logging.getLogger("jarvis.audio.stt")


class SpeechToText:
    """Local, high-speed, zero-cost Speech-To-Text engine."""

    def __init__(
        self,
        model_size: str = "base.en",
        device: str = "cpu",
        compute_type: str = "int8",
        sample_rate: int = 16000,
        lazy_load: bool = True,
    ):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.sample_rate = sample_rate
        self._whisper_model = None
        self._sr_recognizer = None
        if not lazy_load:
            self._ensure_engine()

    def _ensure_engine(self) -> None:
        if self._whisper_model is not None or self._sr_recognizer is not None:
            return
        try:
            from faster_whisper import WhisperModel
            logger.info(f"Loading faster-whisper ({self.model_size}) on {self.device}...")
            self._whisper_model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
            )
            logger.info("faster-whisper model ready.")
        except Exception as e:
            logger.warning(f"Could not load faster-whisper: {e}. Falling back to SpeechRecognition.")
            try:
                import speech_recognition as sr
                self._sr_recognizer = sr.Recognizer()
            except ImportError:
                logger.error("No STT engine available. Install faster-whisper or SpeechRecognition.")

    def transcribe(self, audio_bytes: bytes) -> str:
        """Transcribe PCM16 audio bytes to text."""
        if not audio_bytes or len(audio_bytes) < 1000:
            return ""

        self._ensure_engine()

        if self._whisper_model:
            try:
                # Convert PCM16 bytes to float32 normalized array
                audio_np = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
                segments, info = self._whisper_model.transcribe(
                    audio_np,
                    beam_size=5,
                    language="en",
                    vad_filter=True,
                    vad_parameters=dict(min_silence_duration_ms=500),
                )
                text = " ".join([seg.text for seg in segments]).strip()
                return text
            except Exception as e:
                logger.error(f"Whisper transcription failed: {e}")

        # Fallback using SpeechRecognition
        if self._sr_recognizer:
            try:
                import speech_recognition as sr
                # Wrap PCM bytes in a WAV container in memory
                wav_io = io.BytesIO()
                with wave.open(wav_io, "wb") as wav_file:
                    wav_file.setnchannels(1)
                    wav_file.setsampwidth(2)
                    wav_file.setframerate(self.sample_rate)
                    wav_file.writeframes(audio_bytes)
                wav_io.seek(0)

                with sr.AudioFile(wav_io) as source:
                    audio_data = self._sr_recognizer.record(source)
                    text = self._sr_recognizer.recognize_google(audio_data)
                    return text.strip()
            except Exception as e:
                logger.error(f"Fallback recognizer error: {e}")

        return ""
