"""Laptop control tools with Windows native automation, app indexing, and safety checks."""

import ctypes
import os
from pathlib import Path
import subprocess
import time
import webbrowser
from typing import Any, Dict, List, Optional
import psutil
from PIL import ImageGrab
from rapidfuzz import fuzz, process

from jarvis.tools.base import BaseTool, ToolRegistry, ToolResult, PermissionTier
from jarvis.safety.tiers import SecurityPolicy
from jarvis.safety.audit import audit_logger
from jarvis.config import config


class LaptopTools:
    """Windows native automation primitives with cross-platform fallbacks."""

    APP_MAP = {
        "code": "code",
        "vs code": "code",
        "visual studio code": "code",
        "chrome": "chrome",
        "google chrome": "chrome",
        "edge": "msedge",
        "microsoft edge": "msedge",
        "notepad": "notepad",
        "calculator": "calc",
        "calc": "calc",
        "terminal": "wt",
        "windows terminal": "wt",
        "spotify": "spotify",
        "explorer": "explorer",
        "word": "winword",
        "excel": "excel",
    }

    @classmethod
    def open_app(cls, app_name: str, dry_run: bool = False) -> ToolResult:
        clean_name = app_name.lower().strip()

        # Check blocklist
        if SecurityPolicy.is_path_blocked(clean_name) or SecurityPolicy.is_command_blocked(clean_name):
            audit_logger.log("laptop.open_app", {"app_name": app_name}, PermissionTier.TIER_4_BLOCKED, False, False, "Blocked by security policy")
            return ToolResult(success=False, message=f"Access to '{app_name}' is restricted by system security policy.")

        if dry_run:
            return ToolResult(success=True, message=f"[Dry-Run] Would launch application '{app_name}'.")

        # Fuzzy match or resolve alias
        executable = cls.APP_MAP.get(clean_name)
        if not executable:
            best_match, score, _ = process.extractOne(clean_name, list(cls.APP_MAP.keys()), scorer=fuzz.ratio)
            if score >= 60:
                executable = cls.APP_MAP[best_match]
            else:
                executable = clean_name

        try:
            # Launch process via os.startfile or subprocess
            proc = subprocess.Popen(
                executable,
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            # Verification step: wait up to 2 seconds and check if process exists
            time.sleep(1.0)
            verified = False
            for p in psutil.process_iter(['name']):
                if executable.lower() in p.info['name'].lower() or clean_name in p.info['name'].lower():
                    verified = True
                    break

            if not verified:
                # Retry once
                subprocess.Popen(executable, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                time.sleep(1.0)
                for p in psutil.process_iter(['name']):
                    if executable.lower() in p.info['name'].lower():
                        verified = True
                        break

            msg = f"Application '{app_name}' launched successfully." if verified else f"Launched '{app_name}', awaiting window rendering."
            audit_logger.log("laptop.open_app", {"app_name": app_name}, PermissionTier.TIER_1_AUTO, True, True, msg)
            return ToolResult(success=True, message=msg, data={"executable": executable, "verified": verified})
        except Exception as e:
            audit_logger.log("laptop.open_app", {"app_name": app_name}, PermissionTier.TIER_1_AUTO, True, False, str(e), str(e))
            return ToolResult(success=False, message=f"Could not open {app_name}: {str(e)}", error=str(e))

    @classmethod
    def close_app(cls, app_name: str, confirmed: bool = False, dry_run: bool = False) -> ToolResult:
        clean_name = app_name.lower().strip()

        if SecurityPolicy.is_path_blocked(clean_name) or SecurityPolicy.is_command_blocked(clean_name):
            return ToolResult(success=False, message=f"Action blocked by policy for {app_name}.")

        if dry_run:
            return ToolResult(success=True, message=f"[Dry-Run] Would terminate application '{app_name}'.")

        terminated = 0
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                pname = proc.info['name'].lower()
                if clean_name in pname:
                    proc.terminate()
                    terminated += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        if terminated > 0:
            msg = f"Closed {terminated} process(es) matching '{app_name}'."
            audit_logger.log("laptop.close_app", {"app_name": app_name}, PermissionTier.TIER_2_CONFIRM_VOICE, confirmed, True, msg)
            return ToolResult(success=True, message=msg, data={"count": terminated})
        else:
            return ToolResult(success=False, message=f"No active processes found matching '{app_name}'.")

    @classmethod
    def open_site(cls, url: str, dry_run: bool = False) -> ToolResult:
        if not url.startswith("http://") and not url.startswith("https://"):
            url = f"https://{url}"

        if dry_run:
            return ToolResult(success=True, message=f"[Dry-Run] Would navigate to URL {url}.")

        try:
            webbrowser.open(url)
            audit_logger.log("laptop.open_site", {"url": url}, PermissionTier.TIER_1_AUTO, True, True, f"Opened site {url}")
            return ToolResult(success=True, message=f"Navigated to {url}.", data={"url": url})
        except Exception as e:
            return ToolResult(success=False, message=f"Failed to open site: {e}", error=str(e))

    @classmethod
    def set_volume(cls, level: int, dry_run: bool = False) -> ToolResult:
        level = max(0, min(100, int(level)))
        if dry_run:
            return ToolResult(success=True, message=f"[Dry-Run] Would set system volume to {level} percent.")

        # Native Windows volume adjustment using media keys or PowerShell audio
        try:
            user32 = ctypes.windll.user32
            # Each VK_VOLUME_UP/DOWN moves by 2%
            # Reset to 0 with 50 down presses, then step up
            for _ in range(50):
                user32.keybd_event(0xAE, 0, 0, 0)
                user32.keybd_event(0xAE, 0, 2, 0)
            steps_up = level // 2
            for _ in range(steps_up):
                user32.keybd_event(0xAF, 0, 0, 0)
                user32.keybd_event(0xAF, 0, 2, 0)

            audit_logger.log("laptop.set_volume", {"level": level}, PermissionTier.TIER_1_AUTO, True, True, f"Volume set to {level}%")
            return ToolResult(success=True, message=f"Master volume adjusted to {level} percent.", data={"level": level})
        except Exception as e:
            return ToolResult(success=False, message=f"Failed to adjust volume: {e}", error=str(e))

    @classmethod
    def media_control(cls, action: str, dry_run: bool = False) -> ToolResult:
        action = action.lower().strip()
        if dry_run:
            return ToolResult(success=True, message=f"[Dry-Run] Would trigger media action '{action}'.")

        key_map = {
            "mute": 0xAD,
            "play": 0xB3,
            "pause": 0xB3,
            "play_pause": 0xB3,
            "next": 0xB0,
            "previous": 0xB1,
            "prev": 0xB1,
        }
        vk = key_map.get(action)
        if not vk:
            return ToolResult(success=False, message=f"Unsupported media action: {action}")

        try:
            user32 = ctypes.windll.user32
            user32.keybd_event(vk, 0, 0, 0)
            user32.keybd_event(vk, 0, 2, 0)
            audit_logger.log("laptop.media_control", {"action": action}, PermissionTier.TIER_1_AUTO, True, True, f"Media action {action} triggered")
            return ToolResult(success=True, message=f"Media {action} executed.", data={"action": action})
        except Exception as e:
            return ToolResult(success=False, message=f"Media control failed: {e}", error=str(e))

    @classmethod
    def lock_screen(cls, dry_run: bool = False) -> ToolResult:
        if dry_run:
            return ToolResult(success=True, message="[Dry-Run] Would lock workstation.")

        try:
            ctypes.windll.user32.LockWorkStation()
            audit_logger.log("laptop.lock_screen", {}, PermissionTier.TIER_1_AUTO, True, True, "Workstation locked")
            return ToolResult(success=True, message="Workstation locked, sir.")
        except Exception as e:
            return ToolResult(success=False, message=f"Could not lock screen: {e}", error=str(e))

    @classmethod
    def take_screenshot(cls, filename: Optional[str] = None, dry_run: bool = False) -> ToolResult:
        desktop_dir = Path.home() / "Desktop"
        save_path = desktop_dir / (filename or f"screenshot_{int(time.time())}.png")

        if dry_run:
            return ToolResult(success=True, message=f"[Dry-Run] Would save screenshot to {save_path.name}.")

        try:
            img = ImageGrab.grab()
            img.save(str(save_path))
            audit_logger.log("laptop.take_screenshot", {"path": str(save_path)}, PermissionTier.TIER_1_AUTO, True, True, f"Screenshot saved to {save_path.name}")
            return ToolResult(success=True, message=f"Screenshot captured and saved to your desktop as {save_path.name}.", data={"path": str(save_path)})
        except Exception as e:
            return ToolResult(success=False, message=f"Screenshot capture failed: {e}", error=str(e))

    @classmethod
    def search_files(cls, query: str, directory: Optional[str] = None, dry_run: bool = False) -> ToolResult:
        if dry_run:
            return ToolResult(success=True, message=f"[Dry-Run] Would search for files matching '{query}'.")

        search_root = Path(directory) if directory else Path.home()
        matched_files = []

        try:
            # Safely scan search roots (Desktop, Documents, Downloads)
            roots = [Path.home() / "Desktop", Path.home() / "Documents", Path.home() / "Downloads"]
            if directory:
                roots = [Path(directory)]

            for root in roots:
                if not root.exists():
                    continue
                for path in root.rglob(f"*{query}*"):
                    # Check path blocklist
                    if SecurityPolicy.is_path_blocked(str(path)):
                        continue
                    if path.is_file():
                        matched_files.append(str(path))
                        if len(matched_files) >= 5:
                            break
                if len(matched_files) >= 5:
                    break

            if matched_files:
                names = [Path(p).name for p in matched_files]
                return ToolResult(
                    success=True,
                    message=f"Found {len(matched_files)} matching file(s): {', '.join(names)}.",
                    data={"files": matched_files},
                )
            else:
                return ToolResult(success=True, message=f"No files matching '{query}' were found in your primary directories.")
        except Exception as e:
            return ToolResult(success=False, message=f"File search failed: {e}", error=str(e))

    @classmethod
    def run_routine(cls, routine_name: str, dry_run: bool = False) -> ToolResult:
        routine = config.routines.get(routine_name)
        if not routine:
            return ToolResult(success=False, message=f"Routine '{routine_name}' is not configured.")

        actions = routine.get("actions", [])
        if dry_run:
            return ToolResult(success=True, message=f"[Dry-Run] Would execute {len(actions)} step(s) of routine '{routine_name}'.")

        executed = 0
        registry = ToolRegistry.get_instance()
        for act in actions:
            tool_name = act.get("tool")
            params = act.get("params", {})
            t = registry.get_tool(tool_name)
            if t:
                t.execute(params)
                executed += 1

        msg = f"Routine '{routine_name}' completed ({executed} action(s) executed)."
        audit_logger.log("laptop.run_routine", {"routine_name": routine_name}, PermissionTier.TIER_1_AUTO, True, True, msg)
        return ToolResult(success=True, message=msg, data={"executed": executed})


# Individual Tool wrappers registered into ToolRegistry

class OpenAppTool(BaseTool):
    name = "laptop.open_app"
    description = "Launch an application on the laptop by name."
    tier = PermissionTier.TIER_1_AUTO

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {"app_name": {"type": "string", "description": "Application name or alias"}},
            "required": ["app_name"],
        }

    def validate_params(self, params: Dict[str, Any]) -> bool:
        return "app_name" in params and isinstance(params["app_name"], str)

    def execute(self, params: Dict[str, Any], dry_run: bool = False) -> ToolResult:
        if not self.validate_params(params):
            return ToolResult(success=False, message="Invalid parameters: 'app_name' required.")
        return LaptopTools.open_app(params["app_name"], dry_run=dry_run)


class CloseAppTool(BaseTool):
    name = "laptop.close_app"
    description = "Close or terminate an active application."
    tier = PermissionTier.TIER_2_CONFIRM_VOICE

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {"app_name": {"type": "string", "description": "Name of the app to close"}},
            "required": ["app_name"],
        }

    def validate_params(self, params: Dict[str, Any]) -> bool:
        return "app_name" in params

    def execute(self, params: Dict[str, Any], dry_run: bool = False) -> ToolResult:
        return LaptopTools.close_app(params["app_name"], confirmed=True, dry_run=dry_run)


class OpenSiteTool(BaseTool):
    name = "laptop.open_site"
    description = "Open a webpage URL in the default browser."
    tier = PermissionTier.TIER_1_AUTO

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {"url": {"type": "string", "description": "URL to open"}},
            "required": ["url"],
        }

    def validate_params(self, params: Dict[str, Any]) -> bool:
        return "url" in params

    def execute(self, params: Dict[str, Any], dry_run: bool = False) -> ToolResult:
        return LaptopTools.open_site(params["url"], dry_run=dry_run)


class SetVolumeTool(BaseTool):
    name = "laptop.set_volume"
    description = "Set the system master volume level from 0 to 100 percent."
    tier = PermissionTier.TIER_1_AUTO

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {"level": {"type": "integer", "minimum": 0, "maximum": 100}},
            "required": ["level"],
        }

    def validate_params(self, params: Dict[str, Any]) -> bool:
        return "level" in params and isinstance(params["level"], (int, float))

    def execute(self, params: Dict[str, Any], dry_run: bool = False) -> ToolResult:
        return LaptopTools.set_volume(params["level"], dry_run=dry_run)


class MediaControlTool(BaseTool):
    name = "laptop.media_control"
    description = "Control audio media playback: play, pause, next, previous, mute."
    tier = PermissionTier.TIER_1_AUTO

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {"action": {"type": "string", "enum": ["play", "pause", "next", "previous", "mute"]}},
            "required": ["action"],
        }

    def validate_params(self, params: Dict[str, Any]) -> bool:
        return "action" in params

    def execute(self, params: Dict[str, Any], dry_run: bool = False) -> ToolResult:
        return LaptopTools.media_control(params["action"], dry_run=dry_run)


class LockScreenTool(BaseTool):
    name = "laptop.lock_screen"
    description = "Instantly lock the laptop workstation."
    tier = PermissionTier.TIER_1_AUTO

    def get_schema(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {}}

    def validate_params(self, params: Dict[str, Any]) -> bool:
        return True

    def execute(self, params: Dict[str, Any], dry_run: bool = False) -> ToolResult:
        return LaptopTools.lock_screen(dry_run=dry_run)


class TakeScreenshotTool(BaseTool):
    name = "laptop.take_screenshot"
    description = "Capture the screen and save to the desktop."
    tier = PermissionTier.TIER_1_AUTO

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {"filename": {"type": "string"}},
        }

    def validate_params(self, params: Dict[str, Any]) -> bool:
        return True

    def execute(self, params: Dict[str, Any], dry_run: bool = False) -> ToolResult:
        return LaptopTools.take_screenshot(params.get("filename"), dry_run=dry_run)


class SearchFilesTool(BaseTool):
    name = "laptop.search_files"
    description = "Search local files safely across user directories."
    tier = PermissionTier.TIER_1_AUTO

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "directory": {"type": "string"},
            },
            "required": ["query"],
        }

    def validate_params(self, params: Dict[str, Any]) -> bool:
        return "query" in params

    def execute(self, params: Dict[str, Any], dry_run: bool = False) -> ToolResult:
        return LaptopTools.search_files(params["query"], params.get("directory"), dry_run=dry_run)


class RunRoutineTool(BaseTool):
    name = "laptop.run_routine"
    description = "Execute a configured multi-step routine."
    tier = PermissionTier.TIER_1_AUTO

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {"routine_name": {"type": "string"}},
            "required": ["routine_name"],
        }

    def validate_params(self, params: Dict[str, Any]) -> bool:
        return "routine_name" in params

    def execute(self, params: Dict[str, Any], dry_run: bool = False) -> ToolResult:
        return LaptopTools.run_routine(params["routine_name"], dry_run=dry_run)


# Register laptop tools
_registry = ToolRegistry.get_instance()
_registry.register(OpenAppTool())
_registry.register(CloseAppTool())
_registry.register(OpenSiteTool())
_registry.register(SetVolumeTool())
_registry.register(MediaControlTool())
_registry.register(LockScreenTool())
_registry.register(TakeScreenshotTool())
_registry.register(SearchFilesTool())
_registry.register(RunRoutineTool())
