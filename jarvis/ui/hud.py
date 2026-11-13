"""Lightweight UI HUD and system status indicators."""

import logging
from rich.console import Console
from rich.panel import Panel
from jarvis.core.state import JarvisState

logger = logging.getLogger("jarvis.ui.hud")
console = Console()


class StatusHUD:
    """Renders real-time conversational state transitions."""

    STATE_COLORS = {
        JarvisState.IDLE: "blue",
        JarvisState.LISTENING: "green",
        JarvisState.THINKING: "yellow",
        JarvisState.ACTING: "magenta",
        JarvisState.SPEAKING: "cyan",
        JarvisState.WAITING_CONFIRMATION: "bright_red",
        JarvisState.INTERRUPTED: "red",
        JarvisState.SHUTDOWN: "dim",
    }

    @classmethod
    def display_state(cls, state: JarvisState, details: str = "") -> None:
        color = cls.STATE_COLORS.get(state, "white")
        badge = f"[{color} bold]● {state.value.upper()}[/{color} bold]"
        if details:
            console.print(f"{badge} [dim]— {details}[/dim]")
        else:
            console.print(badge)
