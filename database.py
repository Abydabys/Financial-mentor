import sqlite3
import logging
from datetime import datetime
from typing import Optional, List, Tuple

logger = logging.getLogger(__name__)

DB_PATH = "financial_bot.db"


class Database:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Initialize database tables."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER UNIQUE NOT NULL,
                    username TEXT DEFAULT '',
                    full_name TEXT DEFAULT '',
                    created_at TEXT DEFAULT (datetime('now'))
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS goals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    description TEXT NOT NULL,
                    goal_amount REAL NOT NULL,
                    current_amount REAL DEFAULT 0,
                    deadline TEXT NOT NULL,
                    created_at TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)

            conn.commit()
        logger.info("Database initialized successfully.")

    def add_user(self, telegram_id: int, username: str = "", full_name: str = "") -> int:
        """Add a new user or ignore if exists. Returns internal user id."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO users (telegram_id, username, full_name)
                VALUES (?, ?, ?)
            """, (telegram_id, username, full_name))
            conn.commit()

            cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
            row = cursor.fetchone()
            return row["id"] if row else None

    def get_user_id(self, telegram_id: int) -> Optional[int]:
        """Get internal user ID from telegram_id."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
            row = cursor.fetchone()
            return row["id"] if row else None

    def add_goal(
        self,
        user_id: int,
        description: str,
        goal_amount: float,
        deadline: str,
    ) -> int:
        """Add a new financial goal. Returns goal id."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO goals (user_id, description, goal_amount, current_amount, deadline)
                VALUES (?, ?, ?, 0, ?)
            """, (user_id, description, goal_amount, deadline))
            conn.commit()
            return cursor.lastrowid

    def get_user_goals(self, user_id: int) -> List[Tuple]:
        """Get all goals for a user."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, description, goal_amount, current_amount, deadline, created_at
                FROM goals
                WHERE user_id = ?
                ORDER BY created_at DESC
            """, (user_id,))
            rows = cursor.fetchall()
            return [tuple(row) for row in rows]

    def get_goal_by_id(self, goal_id: int, user_id: int) -> Optional[Tuple]:
        """Get a specific goal by id and user_id (for security)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, description, goal_amount, current_amount, deadline, created_at
                FROM goals
                WHERE id = ? AND user_id = ?
            """, (goal_id, user_id))
            row = cursor.fetchone()
            return tuple(row) if row else None

    def update_progress(self, goal_id: int, current_amount: float) -> bool:
        """Update the current_amount for a goal."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE goals SET current_amount = ? WHERE id = ?
            """, (current_amount, goal_id))
            conn.commit()
            return cursor.rowcount > 0

    def delete_goal(self, goal_id: int, user_id: int) -> bool:
        """Delete a goal (must belong to user)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM goals WHERE id = ? AND user_id = ?
            """, (goal_id, user_id))
            conn.commit()
            return cursor.rowcount > 0

    def get_user_stats(self, user_id: int) -> dict:
        """Get aggregate stats for a user."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    COUNT(*) as total_goals,
                    SUM(goal_amount) as total_target,
                    SUM(current_amount) as total_saved,
                    SUM(CASE WHEN current_amount >= goal_amount THEN 1 ELSE 0 END) as completed_goals
                FROM goals WHERE user_id = ?
            """, (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else {}
