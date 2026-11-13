"""Tests for Memory tool and persistence."""

import os
import pytest
from jarvis.tools.memory import MemoryEngine, StoreMemoryTool, RecallMemoryTool
from jarvis.tools.base import ToolRegistry


def test_memory_engine_crud(tmp_path):
    db_file = tmp_path / "test_mem.db"
    mem = MemoryEngine(str(db_file))

    # Store
    assert mem.store("dentist", "Dr. Robert Smith, phone 555-0199", "contact") is True
    assert mem.store("coffee preference", "Black, no sugar", "preference") is True

    # Recall
    results = mem.recall("dentist")
    assert len(results) == 1
    assert "Dr. Robert Smith" in results[0]["value"]

    results_coffee = mem.recall("coffee")
    assert len(results_coffee) == 1
    assert "Black, no sugar" in results_coffee[0]["value"]

    # Overwrite / update
    assert mem.store("coffee preference", "Espresso with oat milk", "preference") is True
    updated = mem.recall("coffee")
    assert "Espresso with oat milk" in updated[0]["value"]

    # Delete
    assert mem.delete("dentist") is True
    assert len(mem.recall("dentist")) == 0


def test_memory_tools_via_registry():
    registry = ToolRegistry.get_instance()
    store_tool = registry.get_tool("memory.store")
    recall_tool = registry.get_tool("memory.recall")

    assert store_tool is not None
    assert recall_tool is not None

    res_dry = store_tool.execute({"key": "favorite color", "value": "navy blue"}, dry_run=True)
    assert res_dry.success is True
    assert "[Dry-Run]" in res_dry.message
