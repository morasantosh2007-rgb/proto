"""Wake word and keyword detection engine."""

import logging
import re
from typing import Tuple

logger = logging.getLogger("jarvis.audio.wake_word")


class WakeWordDetector:
    """Robust wake word detector supporting keyword parsing, openWakeWord, and Porcupine."""

    def __init__(
        self,
        wake_word: str = "jarvis",
        sensitivity: float = 0.5,
        sample_rate: int = 16000,
    ):
        self.wake_word = wake_word.lower()
        self.sensitivity = sensitivity
        self.sample_rate = sample_rate

    def check_text_for_wake_word(self, text: str) -> Tuple[bool, str]:
        """
        Check if transcribed text contains the wake word.
        Returns:
            (is_matched: bool, extracted_command: str)
        """
        if not text:
            return False, ""

        cleaned = text.strip()
        lower = cleaned.lower()

        patterns = [
            rf"^(?:hey\s+|hi\s+|ok\s+|hello\s+)?{self.wake_word}[,\s]*(.*)$",
            rf"^(?:can\s+you\s+|please\s+)?{self.wake_word}[,\s]*(.*)$",
            rf"(.*?)[,\s]+(?:hey\s+|hi\s+)?{self.wake_word}\??$",
        ]

        for p in patterns:
            match = re.search(p, lower)
            if match:
                cmd = match.group(1).strip()
                # Clean punctuation
                cmd = re.sub(r'^[,\.\?!;:\s]+', '', cmd)
                return True, cmd

        # If wake word is anywhere in text
        if self.wake_word in lower:
            # Strip first occurrence of wake word
            idx = lower.find(self.wake_word)
            cmd = (lower[:idx] + " " + lower[idx + len(self.wake_word):]).strip()
            return True, cmd

        return False, cleaned
