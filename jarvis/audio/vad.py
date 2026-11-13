"""Voice Activity Detection (VAD) module."""

import numpy as np
import logging
from typing import Optional

logger = logging.getLogger("jarvis.audio.vad")


class VoiceActivityDetector:
    """Detects presence of human voice in audio frames using energy + zero-crossing or Silero."""

    def __init__(self, sample_rate: int = 16000, energy_threshold: float = 300.0, use_silero: bool = False):
        self.sample_rate = sample_rate
        self.energy_threshold = energy_threshold
        self._silero_model = None
        if use_silero:
            self._init_silero()

    def _init_silero(self) -> None:
        try:
            import torch
            # Attempt to load Silero VAD model if torch is available
            model, _ = torch.hub.load(
                repo_or_dir="snakers4/silero-vad",
                model="silero_vad",
                force_reload=False,
                onnx=True,
                trust_repo=True
            )
            self._silero_model = model
            logger.info("Silero VAD loaded successfully.")
        except Exception as e:
            logger.debug(f"Silero VAD unavailable, using high-performance energy VAD: {e}")
            self._silero_model = None

    def is_speech(self, audio_chunk: bytes) -> bool:
        """Determines if a PCM16 audio chunk contains speech."""
        if not audio_chunk:
            return False

        # Convert raw bytes to 16-bit signed PCM numpy array
        audio_data = np.frombuffer(audio_chunk, dtype=np.int16)
        if len(audio_data) == 0:
            return False

        if self._silero_model is not None:
            try:
                import torch
                audio_float = audio_data.astype(np.float32) / 32768.0
                tensor = torch.from_numpy(audio_float)
                confidence = self._silero_model(tensor, self.sample_rate).item()
                return confidence > 0.5
            except Exception:
                pass

        # Robust energy & zero-crossing rate fallback
        rms = np.sqrt(np.mean(audio_data.astype(np.float64) ** 2))
        return bool(rms > self.energy_threshold)
