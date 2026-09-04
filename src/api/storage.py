import os
import json
import sqlite3
import threading
from contextlib import contextmanager
from typing import Optional, List, Dict, Any
from .schemas import TaskStatusResponse

DEFAULT_DB_PATH = os.getenv("TASKS_DB_PATH", "tasks.db")

class TaskStorage:
    """
    SQLite-backed persistent task store for API background jobs.
    Thread-safe, survives server restarts, and supports multi-worker deployments.
    """

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._init_db()

    @contextmanager
    def _connection(self):
        conn = sqlite3.connect(self.db_path, timeout=15.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self):
        with self._lock:
            with self._connection() as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS tasks (
                        task_id TEXT PRIMARY KEY,
                        status TEXT NOT NULL,
                        url TEXT NOT NULL,
                        records_count INTEGER NOT NULL DEFAULT 0,
                        records TEXT,
                        error_message TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                    """
                )
                conn.commit()

    def create_task(self, task_id: str, url: str) -> TaskStatusResponse:
        task = TaskStatusResponse(
            task_id=task_id,
            status="pending",
            url=url,
            records_count=0,
            records=None,
            error_message=None,
        )
        with self._lock:
            with self._connection() as conn:
                conn.execute(
                    """
                    INSERT INTO tasks (task_id, status, url, records_count, records, error_message, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """,
                    (task_id, "pending", url, 0, None, None),
                )
                conn.commit()
        return task

    def update_task_status(
        self,
        task_id: str,
        status: str,
        records_count: int = 0,
        records: Optional[List[Dict[str, Any]]] = None,
        error_message: Optional[str] = None,
    ) -> Optional[TaskStatusResponse]:
        records_json = json.dumps(records) if records is not None else None
        with self._lock:
            with self._connection() as conn:
                conn.execute(
                    """
                    UPDATE tasks
                    SET status = ?, records_count = ?, records = ?, error_message = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE task_id = ?
                    """,
                    (status, records_count, records_json, error_message, task_id),
                )
                conn.commit()
        return self.get_task(task_id)

    def get_task(self, task_id: str) -> Optional[TaskStatusResponse]:
        with self._lock:
            with self._connection() as conn:
                cur = conn.execute(
                    "SELECT task_id, status, url, records_count, records, error_message FROM tasks WHERE task_id = ?",
                    (task_id,),
                )
                row = cur.fetchone()
                if not row:
                    return None

                records = json.loads(row["records"]) if row["records"] else None
                return TaskStatusResponse(
                    task_id=row["task_id"],
                    status=row["status"],
                    url=row["url"],
                    records_count=row["records_count"],
                    records=records,
                    error_message=row["error_message"],
                )

    def list_tasks(self, limit: int = 50, include_records: bool = False) -> List[TaskStatusResponse]:
        with self._lock:
            with self._connection() as conn:
                cur = conn.execute(
                    """
                    SELECT task_id, status, url, records_count, records, error_message 
                    FROM tasks 
                    ORDER BY created_at DESC 
                    LIMIT ?
                    """,
                    (limit,),
                )
                rows = cur.fetchall()
                results = []
                for row in rows:
                    records = None
                    if include_records and row["records"]:
                        records = json.loads(row["records"])
                    results.append(
                        TaskStatusResponse(
                            task_id=row["task_id"],
                            status=row["status"],
                            url=row["url"],
                            records_count=row["records_count"],
                            records=records,
                            error_message=row["error_message"],
                        )
                    )
                return results

    def delete_task(self, task_id: str) -> bool:
        with self._lock:
            with self._connection() as conn:
                cur = conn.execute("DELETE FROM tasks WHERE task_id = ?", (task_id,))
                conn.commit()
                return cur.rowcount > 0

    def clear_all(self):
        """Helper for testing: clears all tasks."""
        with self._lock:
            with self._connection() as conn:
                conn.execute("DELETE FROM tasks")
                conn.commit()
