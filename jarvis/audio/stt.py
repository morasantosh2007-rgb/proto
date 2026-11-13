"""Speech-To-Text (STT) implementation with anti-hallucination guards."""

import io
import logging
import os
import wave
from typing import List, Optional
import numpy as np

logger = logging.getLogger("jarvis.audio.stt")

# Common Whisper hallucinations when fed low-volume background noise
HALLUCINATION_PHRASES = {
    "are listening",
    "i never do this this",
    "thank you for watching",
    "thanks for watching",
    "subtitles by",
    "subtitled by",
    "please subscribe",
    "subscribe to my channel",
    "good",
    "you",
    "the end",
    "bye",
    "silence",
    "amara.org",
}


class SpeechToText:
    """Local Speech-To-Text engine with whisper hallucination suppression."""

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
        """Transcribe PCM16 audio bytes with noise and hallucination filtering."""
        # Minimum audio length: at least ~0.7 seconds (22,400 bytes) to avoid noise clicks
        min_bytes = int(self.sample_rate * 2 * 0.7)
        if not audio_bytes or len(audio_bytes) < min_bytes:
            return ""

        self._ensure_engine()

        if self._whisper_model:
            try:
                # Convert PCM16 bytes to float32 normalized array
                audio_np = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0

                # Check audio RMS energy to ensure it's not pure silence
                rms = np.sqrt(np.mean(audio_np ** 2))
                if rms < 0.005:  # Very faint background noise
                    return ""

                segments, info = self._whisper_model.transcribe(
                    audio_np,
                    beam_size=5,
                    language="en",
                    condition_on_previous_text=False,
                    vad_filter=True,
                    vad_parameters=dict(min_silence_duration_ms=400),
                )

                valid_segments = []
                for seg in segments:
                    # Filter out segments flagged as non-speech
                    if seg.no_speech_prob < 0.55 and seg.avg_logprob > -1.2:
                        cleaned_seg = seg.text.strip()
                        if cleaned_seg:
                            valid_segments.append(cleaned_seg)

                text = " ".join(valid_segments).strip()

                # Clean hallucination check
                check_lower = text.lower().strip(" .!?,;")
                if check_lower in HALLUCINATION_PHRASES:
                    logger.debug(f"Suppressed Whisper hallucination: '{text}'")
                    return ""

                return text
            except Exception as e:
                logger.error(f"Whisper transcription failed: {e}")

        # Fallback using SpeechRecognition
        if self._sr_recognizer:
            try:
                import speech_recognition as sr
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
                logger.debug(f"SpeechRecognition fallback error: {e}")

        return ""
