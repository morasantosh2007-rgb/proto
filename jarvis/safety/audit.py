"""SQLite-backed immutable audit log for JARVIS actions."""

from datetime import datetime
import json
import logging
from pathlib import Path
import sqlite3
from typing import Any, Dict, List, Optional
from jarvis.config import config

logger = logging.getLogger("jarvis.safety.audit")


class AuditLogger:
    """Records every tool invocation, permission tier, confirmation, and outcome."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or config.audit_db_path
        self._init_db()

    def _init_db(self) -> None:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS audit_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        tool_name TEXT NOT NULL,
                        parameters TEXT,
                        tier INTEGER NOT NULL,
                        confirmed INTEGER NOT NULL,
                        success INTEGER NOT NULL,
                        message TEXT,
                        error TEXT
                    )
                    """
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to initialize audit database: {e}")

    def log(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        tier: int,
        confirmed: bool,
        success: bool,
        message: str = "",
        error: Optional[str] = None,
    ) -> None:
        try:
            now_str = datetime.now().isoformat()
            param_str = json.dumps(parameters)
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO audit_log (timestamp, tool_name, parameters, tier, confirmed, success, message, error)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (now_str, tool_name, param_str, tier, 1 if confirmed else 0, 1 if success else 0, message, error or ""),
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Audit log write failed: {e}")

    def get_recent_actions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve recent actions for voice query: 'what did you do today?'"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT timestamp, tool_name, parameters, success, message
                    FROM audit_log
                    ORDER BY id DESC LIMIT ?
                    """,
                    (limit,),
                )
                rows = cursor.fetchall()
                return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"Failed to query audit log: {e}")
            return []


# Global audit logger
audit_logger = AuditLogger()
