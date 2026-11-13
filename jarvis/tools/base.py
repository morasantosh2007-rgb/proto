"""Base classes for JARVIS tool ecosystem."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Dict, List, Optional


class PermissionTier(IntEnum):
    TIER_1_AUTO = 1               # Safe, automatic execution
    TIER_2_CONFIRM_VOICE = 2      # Requires voice confirmation
    TIER_3_PASSPHRASE = 3         # Requires spoken passphrase
    TIER_4_BLOCKED = 4            # Completely prohibited


@dataclass
class ToolResult:
    success: bool
    message: str
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    requires_confirmation: bool = False
    confirmation_prompt: Optional[str] = None

    def to_speech_summary(self) -> str:
        return self.message


class BaseTool(ABC):
    """Abstract Base Class for all JARVIS tools."""

    name: str = ""
    description: str = ""
    tier: PermissionTier = PermissionTier.TIER_1_AUTO

    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        """Returns JSON schema for tool arguments."""
        pass

    @abstractmethod
    def validate_params(self, params: Dict[str, Any]) -> bool:
        """Validates parameter types and boundaries."""
        pass

    @abstractmethod
    def execute(self, params: Dict[str, Any], dry_run: bool = False) -> ToolResult:
        """Executes tool logic with verification."""
        pass


class ToolRegistry:
    """Singleton registry holding all registered JARVIS tools."""

    _instance = None

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    @classmethod
    def get_instance(cls) -> "ToolRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)

    def list_tools(self) -> List[BaseTool]:
        return list(self._tools.values())

    def get_all_schemas(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "tier": int(t.tier),
                "parameters": t.get_schema(),
            }
            for t in self._tools.values()
        ]
