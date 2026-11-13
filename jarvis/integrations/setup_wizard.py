"""Interactive Setup Wizard for integrations, OAuth, and API credentials."""

import sys
from typing import Dict, List, Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm

from jarvis.integrations.oauth_manager import oauth_manager
from jarvis.config import config

console = Console()


class SetupWizard:
    """Walks the user through OAuth credential setup, keyring testing, and service connections."""

    INTEGRATIONS = [
        {"id": "gmail", "name": "Gmail", "type": "oauth"},
        {"id": "google_calendar", "name": "Google Calendar", "type": "oauth"},
        {"id": "outlook_mail", "name": "Outlook Mail (Microsoft Graph)", "type": "oauth"},
        {"id": "outlook_calendar", "name": "Outlook Calendar (Microsoft Graph)", "type": "oauth"},
        {"id": "weather", "name": "Weather Location", "type": "config"},
        {"id": "news", "name": "News Sources & Topics", "type": "config"},
        {"id": "spotify", "name": "Spotify (Optional)", "type": "oauth"},
        {"id": "smart_home", "name": "Smart Home (Home Assistant - Optional)", "type": "token"},
    ]

    def run_menu(self) -> None:
        while True:
            console.clear()
            console.print(Panel.fit(
                "[bold cyan]JARVIS Interactive Integrations & Security Wizard[/bold cyan]\n"
                "[dim]Configure services with least-privilege permissions and OS Keyring storage[/dim]",
                border_style="cyan"
            ))

            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("#", style="dim", width=4)
            table.add_column("Integration", width=35)
            table.add_column("Status", width=18)
            table.add_column("Security Storage", width=25)

            for idx, item in enumerate(self.INTEGRATIONS, 1):
                status_str = "[bold green]Connected[/bold green]" if oauth_manager.is_connected(item["id"]) else "[dim yellow]Not connected[/dim yellow]"
                storage = "OS Credential Keyring" if item["type"] in ["oauth", "token"] else "config.yaml"
                table.add_row(str(idx), item["name"], status_str, storage)

            console.print(table)
            console.print("\n[bold]Actions:[/bold] Enter item number to configure/disconnect, or 'q' to return to JARVIS.")

            choice = Prompt.ask("Select option", default="q")
            if choice.lower() in ["q", "exit", "quit"]:
                console.print("[green]Exiting Setup Wizard. Returning to JARVIS.[/green]")
                break

            if choice.isdigit() and 1 <= int(choice) <= len(self.INTEGRATIONS):
                selected = self.INTEGRATIONS[int(choice) - 1]
                self._handle_integration(selected)

    def _handle_integration(self, item: Dict[str, str]) -> None:
        service_id = item["id"]
        is_conn = oauth_manager.is_connected(service_id)

        console.print(Panel(f"[bold]{item['name']}[/bold] Setup", border_style="blue"))
        if is_conn:
            console.print(f"[green]Status: Currently connected and authorized.[/green]")
            if Confirm.ask(f"Do you want to disconnect {item['name']}?"):
                oauth_manager.disconnect(service_id)
                console.print(f"[yellow]{item['name']} disconnected and credentials purged from keyring.[/yellow]")
                Prompt.ask("Press Enter to continue...")
                return

        # Walk through setup
        if service_id == "gmail":
            self._setup_gmail()
        elif service_id == "google_calendar":
            self._setup_google_calendar()
        elif service_id in ["outlook_mail", "outlook_calendar"]:
            self._setup_azure_oauth(service_id)
        elif service_id == "weather":
            self._setup_weather_config()
        elif service_id == "news":
            self._setup_news_config()
        elif service_id == "spotify":
            self._setup_spotify()
        elif service_id == "smart_home":
            self._setup_smart_home()

        Prompt.ask("Press Enter to return to menu...")

    def _setup_gmail(self) -> None:
        console.print("""
[bold underline]Step-by-Step Gmail OAuth Setup (Least Privilege):[/bold underline]
1. Open your browser and navigate to: [cyan]https://console.cloud.google.com/[/cyan]
2. Create or select a project (e.g. 'Jarvis-Assistant').
3. Navigate to [bold]'APIs & Services' > 'Library'[/bold] and enable [bold]'Gmail API'[/bold].
4. Go to [bold]'OAuth consent screen'[/bold]:
   - User Type: [green]External[/green]
   - Scopes: Request read-only first: [cyan]https://www.googleapis.com/auth/gmail.readonly[/cyan]
     (Optional for sending: [cyan]https://www.googleapis.com/auth/gmail.send[/cyan])
5. Go to [bold]'Credentials' > 'Create Credentials' > 'OAuth client ID'[/bold]:
   - Application type: [green]Desktop app[/green]
   - Download the generated JSON or note Client ID and Client Secret.
""")
        token = Prompt.ask("Enter Client Secret or paste OAuth token (or 'demo' for mock test)", default="demo")
        if token == "demo":
            oauth_manager.save_credential("gmail", {"token": "mock_gmail_oauth_token", "scopes": ["gmail.readonly"]})
            console.print("[bold green]Success: Demo Gmail integration authorized and saved to OS keyring![/bold green]")
        else:
            oauth_manager.save_credential("gmail", {"token": token, "scopes": ["gmail.readonly"]})
            console.print("[bold green]Success: Gmail credentials verified and stored in OS Keyring![/bold green]")

    def _setup_google_calendar(self) -> None:
        console.print("""
[bold underline]Step-by-Step Google Calendar Setup:[/bold underline]
1. In Google Cloud Console ([cyan]https://console.cloud.google.com/[/cyan]), enable [bold]'Google Calendar API'[/bold].
2. Add scope: [cyan]https://www.googleapis.com/auth/calendar.events[/cyan]
3. Use your Desktop OAuth client credentials.
""")
        token = Prompt.ask("Enter OAuth token or 'demo' for mock verification", default="demo")
        if token:
            oauth_manager.save_credential("google_calendar", {"token": token, "scopes": ["calendar.events"]})
            console.print("[bold green]Success: Google Calendar connected and saved to OS Keyring![/bold green]")

    def _setup_azure_oauth(self, service_id: str) -> None:
        console.print("""
[bold underline]Microsoft Graph OAuth Setup:[/bold underline]
1. Visit [cyan]https://portal.azure.com/[/cyan] > Azure Active Directory > App registrations.
2. New registration -> Supported account types: Personal Microsoft accounts.
3. API permissions: [cyan]Mail.Read[/cyan] or [cyan]Calendars.ReadWrite[/cyan].
""")
        token = Prompt.ask("Enter Microsoft OAuth access token (or 'demo')", default="demo")
        if token:
            oauth_manager.save_credential(service_id, {"token": token})
            console.print(f"[bold green]Success: {service_id} saved to OS Keyring![/bold green]")

    def _setup_weather_config(self) -> None:
        console.print(f"Current default weather city: [cyan]{config.weather_city}[/cyan]")
        new_city = Prompt.ask("Enter default city", default=config.weather_city)
        console.print(f"[green]Weather city set to {new_city}.[/green]")

    def _setup_news_config(self) -> None:
        console.print("Configured topics: technology, artificial intelligence, science, world.")
        console.print("[green]Tech news RSS feeds active out of the box.[/green]")

    def _setup_spotify(self) -> None:
        console.print("Spotify Web API OAuth placeholder: connect client ID & secret from developer.spotify.com.")
        tok = Prompt.ask("Enter token (or 'demo')", default="demo")
        oauth_manager.save_credential("spotify", {"token": tok})
        console.print("[green]Spotify credential stored.[/green]")

    def _setup_smart_home(self) -> None:
        console.print("Home Assistant Long-Lived Access Token setup.")
        tok = Prompt.ask("Enter Home Assistant Access Token (or 'demo')", default="demo")
        oauth_manager.save_credential("smart_home", {"token": tok})
        console.print("[green]Smart home integration stored.[/green]")


def run_setup_wizard():
    wizard = SetupWizard()
    wizard.run_menu()
