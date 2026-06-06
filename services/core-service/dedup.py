import os
import sqlite3
import threading


class DedupStore:
    def __init__(self, path=None):
        self.path = path or os.getenv("DEDUP_DB_PATH", "/tmp/core_service_dedup.sqlite3")
        self.lock = threading.Lock()
        self._init_db()

    def _connect(self):
        return sqlite3.connect(self.path, timeout=30)

    def _init_db(self):
        with self._connect() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS processed_events ("
                "event_id TEXT PRIMARY KEY, processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
            )

    def seen(self, event_id):
        with self._connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM processed_events WHERE event_id = ?",
                (event_id,),
            ).fetchone()
        return row is not None

    def mark_processed(self, event_id):
        with self.lock:
            with self._connect() as connection:
                connection.execute(
                    "INSERT OR IGNORE INTO processed_events(event_id) VALUES (?)",
                    (event_id,),
                )
