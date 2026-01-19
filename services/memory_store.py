"""
SQLite Memory Store for Image Curation.

Stores theme-to-query mappings, curated image knowledge,
session history, study plans, and image scoring data
for efficient reuse and learning over time.
"""

import json
import sqlite3
from dataclasses import dataclass
from datetime import date
from typing import Optional
from pathlib import Path
import config


@dataclass
class CuratedImage:
    pexels_id: int
    alt: str
    theme: str
    url: str
    thumbnail: str
    photographer: str


class MemoryStore:
    """SQLite-backed memory store for image curation knowledge."""

    def __init__(self):
        self._conn: Optional[sqlite3.Connection] = None
        self._ensure_db_exists()

    def _ensure_db_exists(self):
        """Create database file directory if needed."""
        db_path = Path(config.SQLITE_DB_PATH)
        db_path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(
                config.SQLITE_DB_PATH,
                check_same_thread=False,  # Allow use from multiple threads (Qt)
                timeout=30.0,
            )
            self._conn.row_factory = sqlite3.Row  # Dict-like access
            # Enable foreign keys
            self._conn.execute("PRAGMA foreign_keys = ON")
        return self._conn

    def init_schema(self):
        """Create tables if they don't exist."""
        cursor = self.conn.cursor()

        # Theme queries table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS theme_queries (
                theme TEXT PRIMARY KEY,
                queries TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Curated images table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS curated_images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pexels_id INTEGER UNIQUE,
                alt TEXT,
                theme TEXT,
                url TEXT,
                thumbnail TEXT,
                photographer TEXT,
                times_used INTEGER DEFAULT 0,
                last_used TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Theme-image mapping
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS theme_images (
                theme TEXT,
                pexels_id INTEGER,
                position INTEGER,
                PRIMARY KEY (theme, pexels_id)
            )
        """)

        # Practice sessions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS practice_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                theme TEXT NOT NULL,
                duration_per_image INTEGER NOT NULL,
                total_images INTEGER NOT NULL,
                images_completed INTEGER DEFAULT 0,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ended_at TIMESTAMP,
                status TEXT DEFAULT 'in_progress'
            )
        """)

        # Session images
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS session_images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER REFERENCES practice_sessions(id) ON DELETE CASCADE,
                pexels_id INTEGER NOT NULL,
                position INTEGER NOT NULL,
                time_spent INTEGER,
                skipped INTEGER DEFAULT 0
            )
        """)

        # Study plans
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS study_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                goal_minutes_per_day INTEGER DEFAULT 30,
                preferred_themes TEXT,
                preferred_duration INTEGER DEFAULT 60,
                active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Daily progress
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plan_id INTEGER REFERENCES study_plans(id) ON DELETE CASCADE,
                date TEXT NOT NULL,
                minutes_practiced INTEGER DEFAULT 0,
                sessions_completed INTEGER DEFAULT 0,
                images_drawn INTEGER DEFAULT 0,
                UNIQUE(plan_id, date)
            )
        """)

        # Image scoring table for feedback
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS image_theme_scores (
                pexels_id INTEGER NOT NULL,
                theme TEXT NOT NULL,
                score REAL DEFAULT 1.0,
                times_shown INTEGER DEFAULT 0,
                last_shown TIMESTAMP,
                PRIMARY KEY (pexels_id, theme)
            )
        """)

        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_curated_images_theme ON curated_images(theme)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_theme_images_theme ON theme_images(theme)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_session_images_pexels ON session_images(pexels_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_session_images_session ON session_images(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_daily_progress_date ON daily_progress(date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_image_scores_theme ON image_theme_scores(theme)")

        self.conn.commit()
        print("[MEMORY] SQLite schema initialized")

    def get_cached_theme(self, theme: str) -> Optional[dict]:
        """
        Check if a theme has cached results.

        Returns dict with 'queries' and 'images' if found, None otherwise.
        """
        theme_lower = theme.lower().strip()

        cursor = self.conn.cursor()

        # Get cached queries for this theme
        cursor.execute(
            "SELECT queries FROM theme_queries WHERE theme = ?",
            (theme_lower,)
        )
        row = cursor.fetchone()
        if not row:
            return None

        # Get cached images for this theme
        cursor.execute("""
            SELECT ci.pexels_id, ci.alt, ci.url, ci.thumbnail, ci.photographer
            FROM curated_images ci
            JOIN theme_images ti ON ci.pexels_id = ti.pexels_id
            WHERE ti.theme = ?
            ORDER BY ti.position
        """, (theme_lower,))
        images = cursor.fetchall()

        if not images:
            return None

        return {
            "queries": json.loads(row["queries"]),
            "images": [dict(img) for img in images]
        }

    def save_theme_results(
        self,
        theme: str,
        queries: list[str],
        images: list[dict]
    ):
        """
        Save curated results for a theme.

        Args:
            theme: The theme/term that was curated
            queries: List of expanded queries used
            images: List of curated image dicts with pexels_id, alt, url, thumbnail, photographer
        """
        theme_lower = theme.lower().strip()

        cursor = self.conn.cursor()

        # Save or update theme queries
        cursor.execute("""
            INSERT INTO theme_queries (theme, queries)
            VALUES (?, ?)
            ON CONFLICT (theme) DO UPDATE SET
                queries = excluded.queries,
                created_at = CURRENT_TIMESTAMP
        """, (theme_lower, json.dumps(queries)))

        # Save images and theme-image mappings
        for position, img in enumerate(images):
            # Upsert image
            cursor.execute("""
                INSERT INTO curated_images (pexels_id, alt, theme, url, thumbnail, photographer)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT (pexels_id) DO UPDATE SET
                    alt = excluded.alt,
                    url = excluded.url,
                    thumbnail = excluded.thumbnail
            """, (
                img["pexels_id"],
                img.get("alt", ""),
                theme_lower,
                img["url"],
                img["thumbnail"],
                img.get("photographer", "")
            ))

            # Create theme-image mapping
            cursor.execute("""
                INSERT INTO theme_images (theme, pexels_id, position)
                VALUES (?, ?, ?)
                ON CONFLICT (theme, pexels_id) DO UPDATE SET position = excluded.position
            """, (theme_lower, img["pexels_id"], position))

        self.conn.commit()

    def get_image_by_id(self, pexels_id: int) -> Optional[dict]:
        """Fetch a single image by its Pexels ID."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT pexels_id, alt, url, thumbnail, photographer FROM curated_images WHERE pexels_id = ?",
            (pexels_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_all_themes(self) -> list[str]:
        """Get list of all cached themes."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT theme FROM theme_queries ORDER BY created_at DESC")
        return [row[0] for row in cursor.fetchall()]

    def get_cached_images_for_theme(self, theme: str) -> list[dict]:
        """Get all images cached for a theme with their scores and usage data."""
        theme_lower = theme.lower().strip()
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT ci.pexels_id, ci.alt, ci.url, ci.thumbnail, ci.photographer,
                   ci.times_used, ci.last_used,
                   COALESCE(its.score, 1.0) as score
            FROM curated_images ci
            JOIN theme_images ti ON ci.pexels_id = ti.pexels_id
            LEFT JOIN image_theme_scores its
                ON ci.pexels_id = its.pexels_id AND its.theme = ?
            WHERE ti.theme = ?
            ORDER BY ti.position
        """, (theme_lower, theme_lower))
        return [dict(row) for row in cursor.fetchall()]

    def get_all_cached_image_ids(self) -> set[int]:
        """Return set of all pexels_ids currently in cache."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT pexels_id FROM curated_images")
        return {row[0] for row in cursor.fetchall()}

    def update_image_usage(self, pexels_id: int):
        """Increment usage count and update last_used timestamp."""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE curated_images
            SET times_used = times_used + 1, last_used = CURRENT_TIMESTAMP
            WHERE pexels_id = ?
        """, (pexels_id,))
        self.conn.commit()

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Global instance
memory_store = MemoryStore()


def init_memory():
    """Initialize the memory store schema."""
    try:
        memory_store.init_schema()
        return True
    except Exception as e:
        print(f"[MEMORY] Failed to initialize: {e}")
        return False
