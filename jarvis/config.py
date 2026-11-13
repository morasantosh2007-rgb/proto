"""Configuration loader for JARVIS."""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"


class JarvisConfig:
    """Provides validated configuration access for all JARVIS subsystems."""

    def __init__(self, config_dict: Optional[Dict[str, Any]] = None):
        self._raw: Dict[str, Any] = config_dict or {}

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "JarvisConfig":
        config_file = path or DEFAULT_CONFIG_PATH
        if config_file.exists():
            with open(config_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        else:
            data = {}
        return cls(data)

    def get(self, key_path: str, default: Any = None) -> Any:
        keys = key_path.split(".")
        val = self._raw
        for k in keys:
            if isinstance(val, dict) and k in val:
                val = val[k]
            else:
                return default
        return val

    @property
    def user_name(self) -> str:
        return self.get("user.name", "Santosh")

    @property
    def address_as(self) -> str:
        return self.get("user.address_as", "sir")

    @property
    def wake_word(self) -> str:
        return self.get("system.wake_word", "jarvis").lower()

    @property
    def follow_up_window(self) -> float:
        return float(self.get("system.follow_up_window_seconds", 8.0))

    @property
    def tts_voice(self) -> str:
        return self.get("audio.tts_voice", "en-GB-RyanNeural")

    @property
    def tts_rate(self) -> str:
        return self.get("audio.tts_rate", "+0%")

    @property
    def tts_pitch(self) -> str:
        return self.get("audio.tts_pitch", "+0Hz")

    @property
    def tts_engine(self) -> str:
        return self.get("audio.tts_engine", "edge-tts")

    @property
    def stt_engine(self) -> str:
        return self.get("audio.stt_engine", "faster-whisper")

    @property
    def whisper_model(self) -> str:
        return self.get("audio.whisper_model", "base.en")

    @property
    def whisper_device(self) -> str:
        return self.get("audio.whisper_device", "cpu")

    @property
    def vad_silence_threshold_ms(self) -> int:
        return int(self.get("audio.vad_silence_threshold_ms", 1200))

    @property
    def brain_provider(self) -> str:
        return self.get("brain.default_provider", "hybrid")

    @property
    def ollama_url(self) -> str:
        return self.get("brain.ollama_url", "http://localhost:11434")

    @property
    def ollama_model(self) -> str:
        return self.get("brain.ollama_model", "llama3.2")

    @property
    def gemini_model(self) -> str:
        return self.get("brain.gemini_model", "gemini-2.5-flash")

    @property
    def blocklist_paths(self) -> List[str]:
        return self.get("safety.blocklist_paths", [".ssh", ".aws", "Windows/System32"])

    @property
    def blocklist_commands(self) -> List[str]:
        return self.get("safety.blocklist_commands", ["format", "regedit"])

    @property
    def audit_db_path(self) -> str:
        return self.get("safety.audit_db_path", "jarvis_audit.db")

    @property
    def routines(self) -> Dict[str, Any]:
        return self.get("routines", {})

    @property
    def news_sources(self) -> List[Dict[str, str]]:
        return self.get("news.sources", [])

    @property
    def weather_city(self) -> str:
        return self.get("weather.default_city", "London")

    @property
    def weather_units(self) -> str:
        return self.get("weather.units", "metric")


# Global singleton instance
config = JarvisConfig.load()
