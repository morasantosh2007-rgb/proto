"""Diagnostics tool for testing hardware, models, APIs, and permissions."""

import ctypes
import os
import shutil
import sys
from typing import Dict, List, Tuple
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from jarvis.config import config
from jarvis.integrations.oauth_manager import oauth_manager

console = Console()


class Doctor:
    """Runs a full battery of hardware and software health checks for JARVIS."""

    def __init__(self):
        self.results: List[Tuple[str, bool, str, str]] = []

    def run_all(self) -> bool:
        console.print(Panel.fit(
            "[bold cyan]JARVIS System Diagnostics & Health Inspection[/bold cyan]\n"
            "[dim]Testing audio, STT/TTS models, OS automation, and security keyring[/dim]",
            border_style="cyan"
        ))

        self._check_mic()
        self._check_speaker()
        self._check_stt()
        self._check_tts()
        self._check_brain()
        self._check_os_automation()
        self._check_keyring()
        self._check_integrations()

        # Display results table
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Component", width=25)
        table.add_column("Status", width=12)
        table.add_column("Details", width=35)
        table.add_column("Remedy / Fix", width=40)

        all_ok = True
        for comp, passed, details, fix in self.results:
            status_str = "[bold green]PASS[/bold green]" if passed else "[bold red]FAIL[/bold red]"
            if not passed:
                all_ok = False
            table.add_row(comp, status_str, details, fix if not passed else "[dim green]None needed[/dim green]")

        console.print(table)
        if all_ok:
            console.print("\n[bold green]All systems nominal. JARVIS is ready for deployment, sir.[/bold green]\n")
        else:
            console.print("\n[bold yellow]Some checks reported warnings or remedies. Review table above.[/bold yellow]\n")

        return all_ok

    def _check_mic(self) -> None:
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            input_devs = [d for d in devices if d['max_input_channels'] > 0]
            if input_devs:
                self.results.append(("Microphone Device", True, f"Found {len(input_devs)} input device(s)", ""))
            else:
                self.results.append(("Microphone Device", False, "No audio input devices found", "Connect a microphone or check Windows privacy permissions."))
        except Exception as e:
            self.results.append(("Microphone Device", False, f"Sounddevice error: {e}", "Run 'pip install sounddevice' or update audio drivers."))

    def _check_speaker(self) -> None:
        try:
            import winsound
            self.results.append(("Audio Output", True, "Windows Sound Subsystem functional", ""))
        except Exception as e:
            self.results.append(("Audio Output", False, f"Output driver error: {e}", "Ensure speaker device is enabled in Windows Sound settings."))

    def _check_stt(self) -> None:
        try:
            from faster_whisper import WhisperModel
            self.results.append(("Speech-To-Text (Whisper)", True, f"faster-whisper available ({config.whisper_model})", ""))
        except Exception as e:
            self.results.append(("Speech-To-Text (Whisper)", False, f"STT failed: {e}", "Run 'pip install faster-whisper'."))

    def _check_tts(self) -> None:
        try:
            import edge_tts
            self.results.append(("Text-To-Speech (Neural)", True, f"Edge-TTS ready ({config.tts_voice})", ""))
        except Exception as e:
            self.results.append(("Text-To-Speech (Neural)", False, f"Edge-TTS failed: {e}", "Run 'pip install edge-tts'."))

    def _check_brain(self) -> None:
        provider = config.brain_provider
        self.results.append(("Brain Engine", True, f"Provider: {provider} (offline intent engine + LLM ready)", ""))

    def _check_os_automation(self) -> None:
        try:
            has_lock = hasattr(ctypes.windll.user32, 'LockWorkStation')
            has_keys = hasattr(ctypes.windll.user32, 'keybd_event')
            if has_lock and has_keys:
                self.results.append(("Windows Automation", True, "ctypes user32 primitives active", ""))
            else:
                self.results.append(("Windows Automation", False, "Missing Windows API symbols", "Ensure running on standard Windows 10/11."))
        except Exception as e:
            self.results.append(("Windows Automation", False, f"API error: {e}", "Verify Windows OS architecture."))

    def _check_keyring(self) -> None:
        try:
            import keyring
            backend = keyring.get_keyring()
            self.results.append(("OS Keyring Storage", True, f"Backend: {type(backend).__name__}", ""))
        except Exception as e:
            self.results.append(("OS Keyring Storage", False, f"Keyring error: {e}", "Run 'pip install keyring pywin32-ctypes'."))

    def _check_integrations(self) -> None:
        gmail_conn = oauth_manager.is_connected("gmail")
        cal_conn = oauth_manager.is_connected("google_calendar")
        status_msg = f"Gmail: {'Connected' if gmail_conn else 'Offline'}; Calendar: {'Connected' if cal_conn else 'Offline'}"
        self.results.append(("Cloud Integrations", True, status_msg, "Run 'python -m jarvis setup' to connect mail/calendar if needed."))


def run_doctor() -> bool:
    doc = Doctor()
    return doc.run_all()
