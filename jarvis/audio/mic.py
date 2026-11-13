"""Microphone audio stream capturing 16kHz 16-bit mono PCM."""

import logging
import queue
import threading
from typing import Generator, Optional

logger = logging.getLogger("jarvis.audio.mic")


class MicrophoneStream:
    """Provides a continuous stream of audio chunks from the default or selected microphone."""

    def __init__(self, sample_rate: int = 16000, chunk_size: int = 1024):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self._queue: queue.Queue = queue.Queue()
        self._running = False
        self._stream = None

    def start(self) -> None:
        if self._running:
            return

        try:
            import sounddevice as sd

            def audio_callback(indata, frames, time_info, status):
                if status:
                    logger.debug(f"Audio callback status: {status}")
                # Convert float32 or int16 numpy array to raw 16-bit PCM bytes
                if indata.dtype == 'float32':
                    pcm_data = (indata * 32767).astype('int16').tobytes()
                else:
                    pcm_data = indata.tobytes()
                self._queue.put(pcm_data)

            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="int16",
                blocksize=self.chunk_size,
                callback=audio_callback,
            )
            self._stream.start()
            self._running = True
            logger.info("Microphone stream started.")
        except Exception as e:
            logger.error(f"Failed to start sounddevice microphone stream: {e}")
            self._running = False

    def read_chunk(self, timeout: float = 0.5) -> Optional[bytes]:
        if not self._running:
            return None
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def stop(self) -> None:
        self._running = False
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
        logger.info("Microphone stream stopped.")
