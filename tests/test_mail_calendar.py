"""Tests for Mail and Calendar tools and Keyring manager."""

import pytest
from jarvis.integrations.oauth_manager import oauth_manager
from jarvis.tools.mail import MailTools, ListMailTool, SendMailTool
from jarvis.tools.calendar import CalendarTools, CreateEventTool
from jarvis.tools.base import ToolRegistry


def test_oauth_manager_lifecycle():
    assert oauth_manager.save_credential("test_service", {"token": "test_token_123"}) is True
    assert oauth_manager.is_connected("test_service") is True
    cred = oauth_manager.get_credential("test_service")
    assert cred["token"] == "test_token_123"

    # Disconnect
    assert oauth_manager.disconnect("test_service") is True


def test_mail_graceful_degradation():
    oauth_manager.disconnect("gmail")
    # When not connected, it should gracefully tell the user how to connect
    res = MailTools.list_messages(dry_run=False)
    assert res.success is True
    assert "not connected" in res.message.lower() or "say 'connect my email'" in res.message.lower()


def test_mail_dry_run_and_confirm():
    res = MailTools.list_messages(dry_run=True)
    assert res.success is True
    assert "unread emails" in res.message

    # Attempt to send without voice confirmation
    send_res = MailTools.send_message("test@example.com", "Test Subject", "Hello", confirmed=False, dry_run=False)
    assert send_res.success is False
    assert send_res.requires_confirmation is True

    # Send with dry run
    send_dry = MailTools.send_message("test@example.com", "Test Subject", "Hello", dry_run=True)
    assert send_dry.success is True
    assert "[Dry-Run]" in send_dry.message


def test_calendar_tools():
    # Dry run list
    res_list = CalendarTools.list_events(dry_run=True)
    assert res_list.success is True
    assert "events scheduled" in res_list.message

    # Create event
    res_create = CalendarTools.create_event("Deep Work Block", "16:00", "17:00", date="today")
    assert res_create.success is True
    assert "Deep Work Block" in res_create.message

    # Conflict detection
    res_conflict = CalendarTools.create_event("Overlap Meeting", "16:15", "16:45", date="today")
    assert res_conflict.success is False
    assert "conflict detected" in res_conflict.message.lower()
