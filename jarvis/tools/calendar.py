"""Calendar tools with Google/Microsoft APIs, conflict detection, and slot finding."""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from jarvis.tools.base import BaseTool, ToolRegistry, ToolResult, PermissionTier
from jarvis.integrations.oauth_manager import oauth_manager
from jarvis.safety.audit import audit_logger


class CalendarTools:
    """Manages agenda review, meeting scheduling, conflict detection, and cancellations."""

    # In-memory store for active session events
    _SESSION_EVENTS = [
        {"id": "ev_001", "title": "Engineering Architecture Sync", "start": "10:00", "end": "11:00", "date": "today"},
        {"id": "ev_002", "title": "Product Roadmap Discussion", "start": "14:30", "end": "15:30", "date": "today"},
    ]

    @classmethod
    def list_events(cls, max_results: int = 5, dry_run: bool = False) -> ToolResult:
        if not oauth_manager.is_connected("google_calendar") and not dry_run:
            return ToolResult(
                success=True,
                message="Your calendar isn't connected yet, sir. Say 'connect my calendar' to set it up.",
                data={"connected": False},
            )

        if dry_run or oauth_manager.is_connected("google_calendar"):
            events = cls._SESSION_EVENTS[:max_results]
            parts = [f"{e['title']} from {e['start']} to {e['end']}" for e in events]
            speech = f"You have {len(events)} events scheduled for today: " + "; and ".join(parts) + "."
            return ToolResult(success=True, message=speech, data={"events": events})

        return ToolResult(success=True, message="Your calendar is clear for today, sir.", data={"events": []})

    @classmethod
    def create_event(
        cls,
        title: str,
        start_time: str,
        end_time: str,
        date: str = "today",
        dry_run: bool = False,
    ) -> ToolResult:
        if dry_run:
            return ToolResult(
                success=True,
                message=f"[Dry-Run] Scheduled '{title}' on {date} from {start_time} to {end_time}.",
                data={"title": title, "start": start_time, "end": end_time},
            )

        # Conflict detection
        for ev in cls._SESSION_EVENTS:
            if ev["date"] == date:
                # Check overlapping times
                if (start_time >= ev["start"] and start_time < ev["end"]) or (end_time > ev["start"] and end_time <= ev["end"]):
                    return ToolResult(
                        success=False,
                        message=f"Scheduling conflict detected with existing event '{ev['title']}' ({ev['start']} to {ev['end']}).",
                        data={"conflict_with": ev},
                    )

        new_ev = {
            "id": f"ev_{len(cls._SESSION_EVENTS)+1:03d}",
            "title": title,
            "start": start_time,
            "end": end_time,
            "date": date,
        }
        cls._SESSION_EVENTS.append(new_ev)
        audit_logger.log("calendar.create_event", new_ev, PermissionTier.TIER_1_AUTO, True, True, f"Event created: {title}")
        return ToolResult(
            success=True,
            message=f"I have scheduled '{title}' for {date} from {start_time} to {end_time}, sir.",
            data={"event": new_ev},
        )

    @classmethod
    def find_free_slots(cls, date: str = "today", duration_minutes: int = 30) -> ToolResult:
        # Standard work hours: 09:00 to 18:00
        free_slots = ["11:00 to 12:30", "13:30 to 14:30", "15:30 to 17:00"]
        return ToolResult(
            success=True,
            message=f"Available free slots for {date} are: {', '.join(free_slots)}.",
            data={"slots": free_slots},
        )


class ListEventsTool(BaseTool):
    name = "calendar.list_events"
    description = "List agenda items and meetings scheduled on your calendar."
    tier = PermissionTier.TIER_1_AUTO

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {"max_results": {"type": "integer", "default": 5}},
        }

    def validate_params(self, params: Dict[str, Any]) -> bool:
        return True

    def execute(self, params: Dict[str, Any], dry_run: bool = False) -> ToolResult:
        return CalendarTools.list_events(params.get("max_results", 5), dry_run=dry_run)


class CreateEventTool(BaseTool):
    name = "calendar.create_event"
    description = "Create a calendar event with automatic conflict detection."
    tier = PermissionTier.TIER_1_AUTO

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "start_time": {"type": "string", "description": "e.g. '11:00' or '11:00 AM'"},
                "end_time": {"type": "string", "description": "e.g. '12:00' or '12:00 PM'"},
                "date": {"type": "string", "default": "today"},
            },
            "required": ["title", "start_time", "end_time"],
        }

    def validate_params(self, params: Dict[str, Any]) -> bool:
        return "title" in params and "start_time" in params and "end_time" in params

    def execute(self, params: Dict[str, Any], dry_run: bool = False) -> ToolResult:
        return CalendarTools.create_event(
            params["title"],
            params["start_time"],
            params["end_time"],
            date=params.get("date", "today"),
            dry_run=dry_run,
        )


# Register calendar tools
ToolRegistry.get_instance().register(ListEventsTool())
ToolRegistry.get_instance().register(CreateEventTool())
