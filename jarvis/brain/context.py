"""Conversation context and dynamic system prompt rendering."""

from datetime import datetime
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional
from jarvis.config import config

PROMPT_TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "prompts" / "jarvis_system_prompt.md"


class ConversationContext:
    """Manages conversational memory, message history, and dynamic prompt templating."""

    def __init__(self, max_history_turns: int = 10):
        self.max_history_turns = max_history_turns
        self.history: List[Dict[str, str]] = []
        self._system_prompt_template = self._load_template()

    def _load_template(self) -> str:
        if PROMPT_TEMPLATE_PATH.exists():
            with open(PROMPT_TEMPLATE_PATH, "r", encoding="utf-8") as f:
                return f.read()
        return "You are JARVIS, a helpful personal assistant."

    def get_system_prompt(self, connected_services: Optional[List[str]] = None) -> str:
        """Render the system prompt dynamically with real-time variables."""
        now = datetime.now()
        dt_str = now.strftime("%A, %B %d, %Y at %I:%M %p")
        services_str = ", ".join(connected_services) if connected_services else "None (Local mode)"
        routines_str = ", ".join(config.routines.keys()) if config.routines else "None configured"

        prompt = self._system_prompt_template
        prompt = prompt.replace("{{USER_NAME}}", config.user_name)
        prompt = prompt.replace("{{USER_ADDRESS_AS}}", config.address_as)
        prompt = prompt.replace("{{CURRENT_DATETIME}}", dt_str)
        prompt = prompt.replace("{{OS_NAME}}", "Windows")
        prompt = prompt.replace("{{CONNECTED_SERVICES}}", services_str)
        prompt = prompt.replace("{{ACTIVE_ROUTINES}}", routines_str)
        return prompt

    def add_user_message(self, text: str) -> None:
        self.history.append({"role": "user", "content": text})
        self._trim_history()

    def add_assistant_message(self, text: str) -> None:
        clean_text = self.sanitize_for_speech(text)
        self.history.append({"role": "assistant", "content": clean_text})
        self._trim_history()

    def _trim_history(self) -> None:
        if len(self.history) > self.max_history_turns * 2:
            self.history = self.history[-(self.max_history_turns * 2):]

    def clear(self) -> None:
        self.history.clear()

    @staticmethod
    def sanitize_for_speech(text: str) -> str:
        """Strip markdown syntax, raw URLs, bullet markers, and emojis for clean speech output."""
        if not text:
            return ""

        # Remove bold, italics, code blocks, headers
        cleaned = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
        cleaned = re.sub(r'`([^`]+)`', r'\1', cleaned)
        cleaned = re.sub(r'[*_#~>]', '', cleaned)

        # Convert bullets to commas
        cleaned = re.sub(r'^\s*[-*+]\s+', '', cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r'^\s*\d+\.\s+', '', cleaned, flags=re.MULTILINE)

        # Remove URLs
        cleaned = re.sub(r'https?://\S+|www\.\S+', 'a web link', cleaned)

        # Remove emojis and extra whitespaces
        cleaned = re.sub(r'[^\w\s.,!?:;\-\'\"$]', '', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()

        return cleaned
