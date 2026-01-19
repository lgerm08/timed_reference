"""
Image Scorer for Feedback-Based Selection.

Handles image scoring based on user feedback, tracks usage,
and provides weighted random selection considering scores and freshness.
"""

import random
import sqlite3
from datetime import datetime
from typing import Optional
import config


# Scoring constants (can be overridden via config)
NEGATIVE_FEEDBACK_DECAY = getattr(config, 'NEGATIVE_FEEDBACK_DECAY', 0.8)
POSITIVE_FEEDBACK_BOOST = getattr(config, 'POSITIVE_FEEDBACK_BOOST', 1.2)
FRESHNESS_BONUS = getattr(config, 'FRESHNESS_BONUS', 0.1)
MIN_SCORE = 0.1  # Minimum score to prevent complete exclusion


class ImageScorer:
    """Handles image scoring and weighted selection."""

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

    def get_score(self, pexels_id: int, theme: str) -> float:
        """
        Get the current score for an image-theme pair.

        Args:
            pexels_id: The Pexels image ID
            theme: The theme context

        Returns:
            Score (default 1.0 if not tracked)
        """
        theme_lower = theme.lower().strip()
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT score FROM image_theme_scores
            WHERE pexels_id = ? AND theme = ?
        """, (pexels_id, theme_lower))
        row = cursor.fetchone()
        return row[0] if row else 1.0

    def record_negative_feedback(self, pexels_id: int, theme: str):
        """
        Record negative feedback - reduces score for this image-theme pair.

        The score is multiplied by NEGATIVE_FEEDBACK_DECAY (default 0.8),
        but never goes below MIN_SCORE.
        """
        theme_lower = theme.lower().strip()
        cursor = self.conn.cursor()

        # Check if record exists
        cursor.execute("""
            SELECT score FROM image_theme_scores
            WHERE pexels_id = ? AND theme = ?
        """, (pexels_id, theme_lower))
        row = cursor.fetchone()

        if row:
            new_score = max(MIN_SCORE, row[0] * NEGATIVE_FEEDBACK_DECAY)
            cursor.execute("""
                UPDATE image_theme_scores
                SET score = ?, times_shown = times_shown + 1, last_shown = CURRENT_TIMESTAMP
                WHERE pexels_id = ? AND theme = ?
            """, (new_score, pexels_id, theme_lower))
        else:
            cursor.execute("""
                INSERT INTO image_theme_scores (pexels_id, theme, score, times_shown, last_shown)
                VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP)
            """, (pexels_id, theme_lower, NEGATIVE_FEEDBACK_DECAY))

        self.conn.commit()

    def record_positive_feedback(self, pexels_id: int, theme: str):
        """
        Record positive feedback - increases score for this image-theme pair.

        The score is multiplied by POSITIVE_FEEDBACK_BOOST (default 1.2),
        capped at 2.0 to prevent runaway scores.
        """
        theme_lower = theme.lower().strip()
        max_score = 2.0
        cursor = self.conn.cursor()

        # Check if record exists
        cursor.execute("""
            SELECT score FROM image_theme_scores
            WHERE pexels_id = ? AND theme = ?
        """, (pexels_id, theme_lower))
        row = cursor.fetchone()

        if row:
            new_score = min(max_score, row[0] * POSITIVE_FEEDBACK_BOOST)
            cursor.execute("""
                UPDATE image_theme_scores
                SET score = ?, times_shown = times_shown + 1, last_shown = CURRENT_TIMESTAMP
                WHERE pexels_id = ? AND theme = ?
            """, (new_score, pexels_id, theme_lower))
        else:
            cursor.execute("""
                INSERT INTO image_theme_scores (pexels_id, theme, score, times_shown, last_shown)
                VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP)
            """, (pexels_id, theme_lower, POSITIVE_FEEDBACK_BOOST))

        self.conn.commit()

    def record_shown(self, pexels_id: int, theme: str):
        """Record that an image was shown (without explicit feedback)."""
        theme_lower = theme.lower().strip()
        cursor = self.conn.cursor()

        # Check if record exists
        cursor.execute("""
            SELECT 1 FROM image_theme_scores
            WHERE pexels_id = ? AND theme = ?
        """, (pexels_id, theme_lower))
        row = cursor.fetchone()

        if row:
            cursor.execute("""
                UPDATE image_theme_scores
                SET times_shown = times_shown + 1, last_shown = CURRENT_TIMESTAMP
                WHERE pexels_id = ? AND theme = ?
            """, (pexels_id, theme_lower))
        else:
            cursor.execute("""
                INSERT INTO image_theme_scores (pexels_id, theme, score, times_shown, last_shown)
                VALUES (?, ?, 1.0, 1, CURRENT_TIMESTAMP)
            """, (pexels_id, theme_lower))

        self.conn.commit()

    def get_image_stats(self, pexels_id: int, theme: str) -> dict:
        """Get full stats for an image-theme pair."""
        theme_lower = theme.lower().strip()
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT score, times_shown, last_shown
            FROM image_theme_scores
            WHERE pexels_id = ? AND theme = ?
        """, (pexels_id, theme_lower))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return {"score": 1.0, "times_shown": 0, "last_shown": None}

    def select_images(
        self,
        available: list[dict],
        theme: str,
        count: int,
        exclude_ids: Optional[set[int]] = None
    ) -> list[dict]:
        """
        Select images using weighted random selection.

        Images with higher scores are more likely to be selected.
        Fresh (unused) images get a bonus.

        Args:
            available: List of image dicts (must have 'pexels_id')
            theme: Theme context for scoring
            count: Number of images to select
            exclude_ids: Set of pexels_ids to exclude

        Returns:
            Selected images (may be fewer than count if not enough available)
        """
        if not available:
            return []

        exclude_ids = exclude_ids or set()
        theme_lower = theme.lower().strip()

        # Filter out excluded images
        candidates = [
            img for img in available
            if img.get('pexels_id', img.get('id')) not in exclude_ids
        ]

        if not candidates:
            return []

        # Get scores for all candidates
        pexels_ids = [img.get('pexels_id', img.get('id')) for img in candidates]

        cursor = self.conn.cursor()
        # SQLite doesn't have ANY(), so we use IN with placeholders
        placeholders = ','.join('?' * len(pexels_ids))
        cursor.execute(f"""
            SELECT pexels_id, score, times_shown
            FROM image_theme_scores
            WHERE pexels_id IN ({placeholders}) AND theme = ?
        """, (*pexels_ids, theme_lower))
        score_map = {row['pexels_id']: dict(row) for row in cursor.fetchall()}

        # Calculate weights
        weights = []
        for img in candidates:
            pexels_id = img.get('pexels_id', img.get('id'))
            stats = score_map.get(pexels_id, {"score": 1.0, "times_shown": 0})

            weight = stats["score"]

            # Add freshness bonus for unused images
            if stats["times_shown"] == 0:
                weight += FRESHNESS_BONUS

            # Check if image has usage data from curated_images
            times_used = img.get('times_used', 0)
            if times_used == 0:
                weight += FRESHNESS_BONUS

            weights.append(max(MIN_SCORE, weight))

        # Weighted random selection without replacement
        selected = []
        remaining_candidates = list(candidates)
        remaining_weights = list(weights)

        select_count = min(count, len(remaining_candidates))
        for _ in range(select_count):
            if not remaining_candidates:
                break

            # Normalize weights
            total_weight = sum(remaining_weights)
            if total_weight <= 0:
                # Fallback to uniform random
                idx = random.randint(0, len(remaining_candidates) - 1)
            else:
                # Weighted random choice
                r = random.uniform(0, total_weight)
                cumulative = 0
                idx = 0
                for i, w in enumerate(remaining_weights):
                    cumulative += w
                    if r <= cumulative:
                        idx = i
                        break

            selected.append(remaining_candidates[idx])
            remaining_candidates.pop(idx)
            remaining_weights.pop(idx)

        return selected

    def get_low_scored_images(self, theme: str, threshold: float = 0.5) -> list[int]:
        """Get pexels_ids with scores below threshold for a theme."""
        theme_lower = theme.lower().strip()
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT pexels_id FROM image_theme_scores
            WHERE theme = ? AND score < ?
        """, (theme_lower, threshold))
        return [row[0] for row in cursor.fetchall()]

    def reset_scores(self, theme: str):
        """Reset all scores for a theme to default (1.0)."""
        theme_lower = theme.lower().strip()
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE image_theme_scores SET score = 1.0 WHERE theme = ?
        """, (theme_lower,))
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
image_scorer = ImageScorer()
