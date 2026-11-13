"""Permission tiers and security boundary definitions."""

from typing import List
from jarvis.tools.base import PermissionTier
from jarvis.config import config


class SecurityPolicy:
    """Enforces execution boundaries, tier classification, and path blocklists."""

    @staticmethod
    def is_path_blocked(path_str: str) -> bool:
        norm = path_str.lower().replace("\\", "/")
        for blocked in config.blocklist_paths:
            if blocked.lower().replace("\\", "/") in norm:
                return True
        return False

    @staticmethod
    def is_command_blocked(cmd_str: str) -> bool:
        low = cmd_str.lower()
        for blocked in config.blocklist_commands:
            if blocked.lower() in low:
                return True
        return False

    @staticmethod
    def get_tier_for_action(action_name: str, target: str = "") -> PermissionTier:
        # Check Tier 4 (blocked)
        if SecurityPolicy.is_path_blocked(target) or SecurityPolicy.is_command_blocked(target):
            return PermissionTier.TIER_4_BLOCKED

        # Tier 3 (passphrase required)
        if any(term in action_name for term in ["delete", "format", "shutdown", "reboot", "shell_exec"]):
            return PermissionTier.TIER_3_PASSPHRASE

        # Tier 2 (voice confirmation required)
        if any(term in action_name for term in ["send_message", "close_app", "install", "rename", "move_file"]):
            return PermissionTier.TIER_2_CONFIRM_VOICE

        # Tier 1 (auto)
        return PermissionTier.TIER_1_AUTO
