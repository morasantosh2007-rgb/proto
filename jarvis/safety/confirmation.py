"""Confirmation engine for Tier 2 and Tier 3 high-risk actions."""

from datetime import datetime, timedelta
import logging
from typing import Any, Callable, Dict, Optional, Tuple
from jarvis.config import config
from jarvis.tools.base import PermissionTier, ToolResult

logger = logging.getLogger("jarvis.safety.confirmation")


class PendingConfirmation:
    def __init__(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        tier: PermissionTier,
        prompt: str,
        timeout_seconds: float = 30.0,
    ):
        self.tool_name = tool_name
        self.parameters = parameters
        self.tier = tier
        self.prompt = prompt
        self.created_at = datetime.now()
        self.expires_at = self.created_at + timedelta(seconds=timeout_seconds)

    def is_expired(self) -> bool:
        return datetime.now() > self.expires_at


class ConfirmationEngine:
    """Tracks pending operations requiring user voice approval."""

    def __init__(self):
        self._pending: Optional[PendingConfirmation] = None

    @property
    def has_pending(self) -> bool:
        if self._pending and self._pending.is_expired():
            self._pending = None
        return self._pending is not None

    def request_confirmation(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        tier: PermissionTier,
        prompt: str,
    ) -> PendingConfirmation:
        self._pending = PendingConfirmation(tool_name, parameters, tier, prompt)
        logger.info(f"Confirmation requested for {tool_name} (Tier {tier.value}): '{prompt}'")
        return self._pending

    def evaluate_response(self, user_voice_text: str) -> Tuple[bool, Optional[PendingConfirmation]]:
        """Evaluates user spoken response against confirmation requirements."""
        if not self.has_pending or not self._pending:
            return False, None

        pending = self._pending
        cleaned = user_voice_text.lower().strip()

        # Check cancellations
        if any(w in cleaned for w in ["cancel", "no", "abort", "stop", "don't do that", "nevermind"]):
            logger.info("User explicitly rejected pending action.")
            self._pending = None
            return False, pending

        # Tier 3 requires specific passphrase
        if pending.tier == PermissionTier.TIER_3_PASSPHRASE:
            passphrase = config.get("safety.tier3_passphrase", "jarvis authorize").lower()
            if passphrase in cleaned:
                logger.info("Passphrase match for Tier 3 action.")
                self._pending = None
                return True, pending
            else:
                logger.warning("Spoken text did not match required passphrase.")
                return False, pending

        # Tier 2 accepts affirmative confirmation
        if pending.tier == PermissionTier.TIER_2_CONFIRM_VOICE:
            affirmatives = ["yes", "proceed", "confirm", "send it", "do it", "sure", "go ahead", "authorized"]
            if any(w in cleaned for w in affirmatives):
                logger.info("User confirmed Tier 2 action.")
                self._pending = None
                return True, pending

        return False, pending

    def clear(self) -> None:
        self._pending = None


# Global confirmation engine
confirmation_engine = ConfirmationEngine()
