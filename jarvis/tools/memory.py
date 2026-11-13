"""Persistent memory engine for user preferences, contacts, corrections, and notes."""

from datetime import datetime
import logging
from pathlib import Path
import sqlite3
from typing import Any, Dict, List, Optional
from jarvis.tools.base import BaseTool, ToolRegistry, ToolResult, PermissionTier
from jarvis.config import config

logger = logging.getLogger("jarvis.tools.memory")


class MemoryEngine:
    """Manages persistent key-value and contextual memory stored in SQLite."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or str(Path(__file__).resolve().parent.parent.parent / "jarvis_memory.db")
        self._init_db()

    def _init_db(self) -> None:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS memories (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        key TEXT UNIQUE NOT NULL,
                        value TEXT NOT NULL,
                        category TEXT DEFAULT 'general',
                        updated_at TEXT NOT NULL
                    )
                    """
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to initialize memory DB: {e}")

    def store(self, key: str, value: str, category: str = "general") -> bool:
        clean_key = key.lower().strip()
        now_str = datetime.now().isoformat()
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO memories (key, value, category, updated_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(key) DO UPDATE SET
                        value = excluded.value,
                        category = excluded.category,
                        updated_at = excluded.updated_at
                    """,
                    (clean_key, value, category, now_str),
                )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Memory store failed for key '{key}': {e}")
            return False

    def recall(self, query: str) -> List[Dict[str, str]]:
        clean_q = query.lower().strip()
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT key, value, category, updated_at
                    FROM memories
                    WHERE key LIKE ? OR value LIKE ?
                    LIMIT 5
                    """,
                    (f"%{clean_q}%", f"%{clean_q}%"),
                )
                rows = cursor.fetchall()
                return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"Memory recall failed for query '{query}': {e}")
            return []

    def list_all(self, category: Optional[str] = None) -> List[Dict[str, str]]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                if category:
                    cursor.execute("SELECT key, value, category FROM memories WHERE category = ?", (category,))
                else:
                    cursor.execute("SELECT key, value, category FROM memories")
                return [dict(r) for r in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to list memories: {e}")
            return []

    def delete(self, key: str) -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM memories WHERE key = ?", (key.lower().strip(),))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to delete memory '{key}': {e}")
            return False


memory_engine = MemoryEngine()


class StoreMemoryTool(BaseTool):
    name = "memory.store"
    description = "Store a user preference, contact, note, or fact in persistent memory."
    tier = PermissionTier.TIER_1_AUTO

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "key": {"type": "string"},
                "value": {"type": "string"},
                "category": {"type": "string", "default": "general"},
            },
            "required": ["key", "value"],
        }

    def validate_params(self, params: Dict[str, Any]) -> bool:
        return "key" in params and "value" in params

    def execute(self, params: Dict[str, Any], dry_run: bool = False) -> ToolResult:
        if dry_run:
            return ToolResult(success=True, message=f"[Dry-Run] Would store memory '{params['key']}': '{params['value']}'.")
        ok = memory_engine.store(params["key"], params["value"], params.get("category", "general"))
        if ok:
            return ToolResult(success=True, message=f"I have noted and remembered that {params['key']} is {params['value']}, sir.")
        return ToolResult(success=False, message="Failed to commit memory to database.")


class RecallMemoryTool(BaseTool):
    name = "memory.recall"
    description = "Search and recall stored facts, preferences, or notes."
    tier = PermissionTier.TIER_1_AUTO

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        }

    def validate_params(self, params: Dict[str, Any]) -> bool:
        return "query" in params

    def execute(self, params: Dict[str, Any], dry_run: bool = False) -> ToolResult:
        if dry_run:
            return ToolResult(success=True, message=f"[Dry-Run] Would recall memories matching '{params['query']}'.")
        results = memory_engine.recall(params["query"])
        if results:
            items = [f"{r['key']}: {r['value']}" for r in results]
            return ToolResult(success=True, message=f"Recalled: {'; '.join(items)}.", data={"memories": results})
        return ToolResult(success=True, message=f"I have no memory regarding '{params['query']}', sir.")


# Register memory tools
ToolRegistry.get_instance().register(StoreMemoryTool())
ToolRegistry.get_instance().register(RecallMemoryTool())
