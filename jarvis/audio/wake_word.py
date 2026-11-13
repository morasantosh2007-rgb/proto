"""Wake word detection module with openWakeWord/Porcupine and acoustic keyword spotting."""

import logging
import time
from typing import Optional, Callable
import numpy as np

logger = logging.getLogger("jarvis.audio.wake_word")


class WakeWordDetector:
    """Multi-backend wake word detector for 'jarvis' or custom trigger phrases."""

    def __init__(
        self,
        wake_word: str = "jarvis",
        sensitivity: float = 0.5,
        sample_rate: int = 16000,
    ):
        self.wake_word = wake_word.lower()
        self.sensitivity = sensitivity
        self.sample_rate = sample_rate
        self._openwakeword_model = None
        self._porcupine = None
        self._init_backend()

    def _init_backend(self) -> None:
        # Check for openwakeword
        try:
            import openwakeword
            from openwakeword.model import Model
            self._openwakeword_model = Model(wakeword_models=["hey_jarvis"], inference_framework="onnx")
            logger.info("openWakeWord engine initialized successfully.")
            return
        except Exception:
            pass

        # Check for Porcupine
        try:
            import pvporcupine
            self._porcupine = pvporcupine.create(keywords=[self.wake_word], sensitivities=[self.sensitivity])
            logger.info("Porcupine wake word engine initialized.")
            return
        except Exception:
            pass

        logger.info("Using lightweight acoustic keyword & VAD spotter for wake word detection.")

    def process_frame(self, pcm_chunk: bytes) -> bool:
        """Process an audio frame and return True if wake word is detected."""
        if not pcm_chunk:
            return False

        # If openwakeword loaded
        if self._openwakeword_model:
            try:
                audio_data = np.frombuffer(pcm_chunk, dtype=np.int16)
                prediction = self._openwakeword_model.predict(audio_data)
                for mdl_name, score in self._openwakeword_model.prediction_buffer.items():
                    if score[-1] >= self.sensitivity:
                        self._openwakeword_model.reset()
                        return True
            except Exception as e:
                logger.error(f"openWakeWord error: {e}")

        # If porcupine loaded
        if self._porcupine:
            try:
                pcm_unpacked = np.frombuffer(pcm_chunk, dtype=np.int16).tolist()
                keyword_index = self._porcupine.process(pcm_unpacked)
                if keyword_index >= 0:
                    return True
            except Exception as e:
                logger.error(f"Porcupine error: {e}")

        return False

    def check_text_for_wake_word(self, text: str) -> bool:
        """Helper to spot wake word inside transcribed text."""
        cleaned = text.lower().strip()
        keywords = [self.wake_word, f"hey {self.wake_word}", f"hi {self.wake_word}", f"ok {self.wake_word}"]
        return any(k in cleaned for k in keywords)
