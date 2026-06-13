from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from app.config import DATA_DIR, DUMP_FILE, DUMP_INTERVAL_SECONDS, DEFAULT_ADMIN_USER, DEFAULT_ADMIN_PASSWORD
from app.models import new_id, now

logger = logging.getLogger(__name__)


class Database:
    def __init__(self):
        self.terms: dict[str, dict] = {}
        self.term_versions: dict[str, list[dict]] = {}
        self.audit_logs: list[dict] = []
        self.users: dict[str, dict] = {}
        self.user_tokens: dict[str, str] = {}
        self.notifications: list[dict] = {}
        self.subscriptions: dict[str, list[str]] = {}
        self.query_history: dict[str, list[dict]] = {}
        self.points_log: list[dict] = []
        self.meetings: dict[str, dict] = {}
        self.recommendation_stats: dict[str, dict] = {"suggested": 0, "adopted": 0}
        self.term_usage: dict[str, dict] = {}
        self.term_co_occurrence: dict[str, dict] = {}
        self.search_co_occurrence: dict[str, dict] = {}
        self.fts_conn: Optional[sqlite3.Connection] = None
        self._dump_task: Optional[asyncio.Task] = None

    def init_fts(self):
        self.fts_conn = sqlite3.connect(":memory:", check_same_thread=False)
        self.fts_conn.execute(
            "CREATE VIRTUAL TABLE IF NOT EXISTS terms_fts USING fts5("
            "term_id, source_term, target_term, definition, domain, source_lang, target_lang"
            ")"
        )
        self.fts_conn.commit()

    def fts_insert(self, term_id: str, source_term: str, target_term: str,
                   definition: str, domain: str, source_lang: str, target_lang: str):
        if not self.fts_conn:
            return
        self.fts_conn.execute(
            "INSERT INTO terms_fts VALUES (?, ?, ?, ?, ?, ?, ?)",
            (term_id, source_term, target_term, definition, domain, source_lang, target_lang),
        )
        self.fts_conn.commit()

    def fts_delete(self, term_id: str):
        if not self.fts_conn:
            return
        self.fts_conn.execute("DELETE FROM terms_fts WHERE term_id = ?", (term_id,))
        self.fts_conn.commit()

    def fts_update(self, term_id: str, source_term: str, target_term: str,
                   definition: str, domain: str, source_lang: str, target_lang: str):
        self.fts_delete(term_id)
        self.fts_insert(term_id, source_term, target_term, definition, domain, source_lang, target_lang)

    def fts_search(self, query: str, limit: int = 50) -> list[str]:
        if not self.fts_conn:
            return []
        cursor = self.fts_conn.execute(
            "SELECT term_id FROM terms_fts WHERE terms_fts MATCH ? LIMIT ?",
            (query, limit),
        )
        return [row[0] for row in cursor.fetchall()]

    def init_default_admin(self):
        if not any(u.get("role") == "admin" for u in self.users.values()):
            admin_id = new_id()
            self.users[admin_id] = {
                "user_id": admin_id,
                "username": DEFAULT_ADMIN_USER,
                "password_hash": hashlib.sha256(DEFAULT_ADMIN_PASSWORD.encode()).hexdigest(),
                "role": "admin",
                "email": "admin@example.com",
                "domains": [],
                "points": 0,
                "created_at": now().isoformat(),
            }

    async def start_dump_loop(self):
        self._dump_task = asyncio.create_task(self._dump_loop())

    async def _dump_loop(self):
        while True:
            await asyncio.sleep(DUMP_INTERVAL_SECONDS)
            try:
                self.dump_to_json()
            except Exception as e:
                logger.error(f"Dump failed: {e}")

    def dump_to_json(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        data = {
            "terms": self.terms,
            "term_versions": self.term_versions,
            "audit_logs": self.audit_logs,
            "users": self.users,
            "subscriptions": self.subscriptions,
            "query_history": self.query_history,
            "points_log": self.points_log,
            "meetings": self.meetings,
            "recommendation_stats": self.recommendation_stats,
            "term_usage": self.term_usage,
            "term_co_occurrence": self.term_co_occurrence,
            "search_co_occurrence": self.search_co_occurrence,
            "dumped_at": now().isoformat(),
        }
        tmp = DUMP_FILE.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        tmp.replace(DUMP_FILE)
        logger.info(f"Dumped to {DUMP_FILE}")

    def load_from_json(self):
        if not DUMP_FILE.exists():
            return
        try:
            with open(DUMP_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.terms = data.get("terms", {})
            self.term_versions = data.get("term_versions", {})
            self.audit_logs = data.get("audit_logs", [])
            self.users = data.get("users", {})
            self.subscriptions = data.get("subscriptions", {})
            self.query_history = data.get("query_history", {})
            self.points_log = data.get("points_log", [])
            self.meetings = data.get("meetings", {})
            self.recommendation_stats = data.get("recommendation_stats", {"suggested": 0, "adopted": 0})
            self.term_usage = data.get("term_usage", {})
            self.term_co_occurrence = data.get("term_co_occurrence", {})
            self.search_co_occurrence = data.get("search_co_occurrence", {})
            for t in self.terms.values():
                self.fts_insert(
                    t["term_id"], t["source_term"], t["target_term"],
                    t.get("definition", ""), t["domain"],
                    t["source_lang"], t["target_lang"],
                )
            logger.info(f"Loaded {len(self.terms)} terms from dump")
        except Exception as e:
            logger.error(f"Load failed: {e}")

    async def shutdown(self):
        if self._dump_task:
            self._dump_task.cancel()
        self.dump_to_json()
        if self.fts_conn:
            self.fts_conn.close()


db = Database()
