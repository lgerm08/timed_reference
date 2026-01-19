"""
Session Store for Practice Session Tracking.

Handles CRUD operations for practice sessions, tracks images
shown in each session, and provides history queries.
"""

import sqlite3
from datetime import datetime, timedelta
from typing import Optional
import config


class SessionStore:
    """SQLite-backed store for practice session data."""

    def __init__(self):
        self._conn: Optional[sqlite3.Connection] = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(
                config.SQLITE_DB_PATH,
                check_same_thread=False,  # Allow use from multiple threads (Qt)
                timeout=30.0,
            )
            self._conn.row_factory = sqlite3.Row  # Dict-like access
            self._conn.execute("PRAGMA foreign_keys = ON")
        return self._conn

    def create_session(
        self,
        theme: str,
        duration_per_image: int,
        total_images: int
    ) -> int:
        """
        Create a new practice session.

        Args:
            theme: The theme/focus of the session
            duration_per_image: Seconds allocated per image
            total_images: Number of images in the session

        Returns:
            The session ID
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO practice_sessions (theme, duration_per_image, total_images)
            VALUES (?, ?, ?)
        """, (theme, duration_per_image, total_images))
        self.conn.commit()
        return cursor.lastrowid

    def add_session_image(
        self,
        session_id: int,
        pexels_id: int,
        position: int
    ):
        """Record an image shown in a session."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO session_images (session_id, pexels_id, position)
            VALUES (?, ?, ?)
        """, (session_id, pexels_id, position))
        self.conn.commit()

    def record_image_interaction(
        self,
        session_id: int,
        pexels_id: int,
        time_spent: Optional[int] = None,
        skipped: bool = False
    ):
        """
        Update image interaction data.

        Args:
            session_id: The session ID
            pexels_id: The Pexels image ID
            time_spent: Actual time spent on image (seconds)
            skipped: Whether the image was skipped
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE session_images
            SET time_spent = ?, skipped = ?
            WHERE session_id = ? AND pexels_id = ?
        """, (time_spent, 1 if skipped else 0, session_id, pexels_id))
        self.conn.commit()

    def complete_session(
        self,
        session_id: int,
        images_completed: int,
        status: str = 'completed'
    ):
        """
        Mark a session as completed.

        Args:
            session_id: The session ID
            images_completed: Number of images actually completed
            status: 'completed' or 'abandoned'
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE practice_sessions
            SET images_completed = ?, ended_at = CURRENT_TIMESTAMP, status = ?
            WHERE id = ?
        """, (images_completed, status, session_id))
        self.conn.commit()

    def get_session(self, session_id: int) -> Optional[dict]:
        """Get session details by ID."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, theme, duration_per_image, total_images,
                   images_completed, started_at, ended_at, status
            FROM practice_sessions
            WHERE id = ?
        """, (session_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_session_images(self, session_id: int) -> list[dict]:
        """Get all images from a session with interaction data."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT si.pexels_id, si.position, si.time_spent, si.skipped,
                   ci.alt, ci.url, ci.thumbnail, ci.photographer
            FROM session_images si
            LEFT JOIN curated_images ci ON si.pexels_id = ci.pexels_id
            WHERE si.session_id = ?
            ORDER BY si.position
        """, (session_id,))
        return [dict(row) for row in cursor.fetchall()]

    def get_images_shown_recently(self, days: int = 7) -> set[int]:
        """
        Get pexels_ids of images shown in the last N days.

        Args:
            days: Number of days to look back

        Returns:
            Set of pexels_ids
        """
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT DISTINCT si.pexels_id
            FROM session_images si
            JOIN practice_sessions ps ON si.session_id = ps.id
            WHERE ps.started_at >= ?
        """, (cutoff,))
        return {row[0] for row in cursor.fetchall()}

    def get_session_history(self, limit: int = 20) -> list[dict]:
        """
        Get recent session history with stats.

        Args:
            limit: Maximum number of sessions to return

        Returns:
            List of session dicts with computed stats
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, theme, duration_per_image, total_images,
                   images_completed, started_at, ended_at, status,
                   CASE
                       WHEN ended_at IS NOT NULL AND started_at IS NOT NULL
                       THEN (julianday(ended_at) - julianday(started_at)) * 86400
                       ELSE NULL
                   END as duration_seconds
            FROM practice_sessions
            ORDER BY started_at DESC
            LIMIT ?
        """, (limit,))
        return [dict(row) for row in cursor.fetchall()]

    def get_total_practice_time(self, days: int = 30) -> int:
        """
        Get total practice time in seconds for the last N days.

        Args:
            days: Number of days to look back

        Returns:
            Total seconds practiced
        """
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT COALESCE(SUM(
                (julianday(ended_at) - julianday(started_at)) * 86400
            ), 0)
            FROM practice_sessions
            WHERE started_at >= ? AND status = 'completed'
        """, (cutoff,))
        return int(cursor.fetchone()[0])

    def get_images_drawn_count(self, days: int = 30) -> int:
        """Get count of images practiced in the last N days."""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT COALESCE(SUM(images_completed), 0)
            FROM practice_sessions
            WHERE started_at >= ? AND status = 'completed'
        """, (cutoff,))
        return int(cursor.fetchone()[0])

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Global instance
session_store = SessionStore()
