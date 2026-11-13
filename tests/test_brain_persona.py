"""Tests for Brain and Persona components."""

import pytest
from jarvis.brain.context import ConversationContext
from jarvis.brain.llm_interface import LocalIntentEngine, HybridBrain, BrainDecision


def test_persona_formatting_and_sanitization():
    ctx = ConversationContext()
    raw = "Here is **bold** and `code` with a link https://github.com/test and bullet:\n- Item 1\n- Item 2"
    clean = ctx.sanitize_for_speech(raw)

    # Markdown symbols should be removed
    assert "**" not in clean
    assert "`" not in clean
    assert "https://" not in clean
    assert "- " not in clean
    assert "Item 1" in clean
    assert "Item 2" in clean


def test_system_prompt_dynamic_rendering():
    ctx = ConversationContext()
    prompt = ctx.get_system_prompt(connected_services=["Gmail", "Weather"])

    assert "JARVIS" in prompt
    assert "Santosh" in prompt
    assert "sir" in prompt
    assert "Gmail" in prompt
    assert "Weather" in prompt


def test_local_intent_engine_matching():
    engine = LocalIntentEngine()

    # Morning briefing
    decision = engine.match("Jarvis give me the morning briefing")
    assert decision is not None
    assert decision.has_tools()
    tool_names = [t["name"] for t in decision.tool_calls]
    assert "system.get_status" in tool_names
    assert "weather.get_current" in tool_names
    assert "calendar.list_events" in tool_names

    # Volume control
    vol_decision = engine.match("set volume to 45")
    assert vol_decision is not None
    assert vol_decision.tool_calls[0]["name"] == "laptop.set_volume"
    assert vol_decision.tool_calls[0]["parameters"]["level"] == 45

    # Multi-step app launch
    multi_decision = engine.match("open chrome and go to youtube")
    assert multi_decision is not None
    assert len(multi_decision.tool_calls) == 2
    assert multi_decision.tool_calls[0]["name"] == "laptop.open_app"
    assert multi_decision.tool_calls[1]["name"] == "laptop.open_site"

    # Lock workstation
    lock_decision = engine.match("lock my laptop")
    assert lock_decision is not None
    assert lock_decision.tool_calls[0]["name"] == "laptop.lock_screen"

    # Screenshot
    screen_decision = engine.match("take a screenshot")
    assert screen_decision is not None
    assert screen_decision.tool_calls[0]["name"] == "laptop.take_screenshot"

    # Tier 2 confirmation check on closing app
    close_decision = engine.match("close chrome")
    assert close_decision is not None
    assert close_decision.requires_confirmation is True


def test_hybrid_brain_fallback():
    brain = HybridBrain()
    decision = brain.process("What is the meaning of quantum computing?")
    assert decision is not None
    assert len(decision.spoken_response) > 0
    assert "sir" in decision.spoken_response


def test_capabilities_and_creator_inquiries():
    engine = LocalIntentEngine()

    # User queries: "tell me what you can do?", "who created you?"
    cap_decision = engine.match("tell me what you can do?")
    assert cap_decision is not None
    assert "personal AI chief of staff" in cap_decision.spoken_response
    assert "sir" in cap_decision.spoken_response

    creator_decision = engine.match("who created you?")
    assert creator_decision is not None
    assert "created by you" in creator_decision.spoken_response
    assert "sir" in creator_decision.spoken_response

    boss_decision = engine.match("who is your boss?")
    assert boss_decision is not None
    assert "exclusively for you" in boss_decision.spoken_response

    nature_decision = engine.match("are you real?")
    assert nature_decision is not None
    assert "artificial intelligence" in nature_decision.spoken_response
