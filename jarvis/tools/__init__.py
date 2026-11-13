"""JARVIS tool implementations and registry loader."""
from jarvis.tools.base import BaseTool, ToolRegistry, ToolResult

# Import all tool modules to populate ToolRegistry
import jarvis.tools.laptop
import jarvis.tools.system
import jarvis.tools.mail
import jarvis.tools.calendar
import jarvis.tools.news
import jarvis.tools.weather
import jarvis.tools.memory

__all__ = ["BaseTool", "ToolRegistry", "ToolResult"]
