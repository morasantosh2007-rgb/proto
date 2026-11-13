"""System hardware vitals, battery, disk, network, and process tools."""

import os
import platform
import shutil
import socket
from typing import Any, Dict
import psutil

from jarvis.tools.base import BaseTool, ToolRegistry, ToolResult, PermissionTier


class SystemTools:
    """Queries hardware vitals, battery status, network connectivity, and storage."""

    @classmethod
    def get_status(cls, dry_run: bool = False) -> ToolResult:
        if dry_run:
            return ToolResult(
                success=True,
                message="[Dry-Run] Battery at 85% plugged in, CPU 12%, Disk 45% used, network online.",
            )

        # Battery
        battery_str = "Desktop power (no battery)"
        battery = psutil.sensors_battery()
        if battery:
            plugged = "plugged in and charging" if battery.power_plugged else "on battery power"
            battery_str = f"battery is at {int(battery.percent)} percent, {plugged}"

        # CPU & Memory
        cpu_pct = psutil.cpu_percent(interval=0.2)
        mem = psutil.virtual_memory()
        mem_pct = int(mem.percent)

        # Disk
        total, used, free = shutil.disk_usage(os.path.abspath(os.sep))
        free_gb = free // (2**30)

        # Network check
        online = cls._check_network()
        net_str = "network is connected and operational" if online else "currently offline"

        msg = (
            f"Your {battery_str}. "
            f"CPU load is at {int(cpu_pct)} percent with {mem_pct} percent memory utilized. "
            f"You have {free_gb} gigabytes free on your main drive, and the {net_str}."
        )

        return ToolResult(
            success=True,
            message=msg,
            data={
                "battery_percent": battery.percent if battery else None,
                "cpu_percent": cpu_pct,
                "memory_percent": mem_pct,
                "free_disk_gb": free_gb,
                "online": online,
            },
        )

    @staticmethod
    def _check_network(timeout: float = 1.0) -> bool:
        try:
            socket.setdefaulttimeout(timeout)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
            return True
        except Exception:
            return False


class SystemStatusTool(BaseTool):
    name = "system.get_status"
    description = "Check laptop hardware vitals, battery, CPU, memory, and connectivity."
    tier = PermissionTier.TIER_1_AUTO

    def get_schema(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {}}

    def validate_params(self, params: Dict[str, Any]) -> bool:
        return True

    def execute(self, params: Dict[str, Any], dry_run: bool = False) -> ToolResult:
        return SystemTools.get_status(dry_run=dry_run)


# Register system tools
ToolRegistry.get_instance().register(SystemStatusTool())
