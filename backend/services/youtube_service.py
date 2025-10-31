"""Utility helpers to integrate YouTube content."""
from __future__ import annotations

from typing import Any

from .. import database


LEVEL_ALIASES = {
    "principiante": "cimientos",
    "intermedio": "estructura",
    "avanzado": "acabados",
}


def list_videos(category: str | None = None, search: str | None = None) -> list[dict[str, Any]]:
    """Return videos from the catalog filtered by category or keyword."""
    query = "SELECT id, title, category, youtube_id, level, description, manual_step FROM videos"
    params: list[str] = []
    filters: list[str] = []

    if category:
        filters.append("category = ?")
        params.append(category)
    if search:
        filters.append("title LIKE ?")
        params.append(f"%{search}%")

    if filters:
        query += " WHERE " + " AND ".join(filters)

    query += " ORDER BY category, title"
    return database.fetch_rows(query, params)


def get_manual_videos(level: str) -> list[dict[str, Any]]:
    alias = LEVEL_ALIASES.get(level, level)
    rows = list_videos(category=alias)
    if not rows:
        rows = list_videos()
    return rows[:3]


def get_step_video(level: str) -> dict[str, Any] | None:
    videos = get_manual_videos(level)
    return videos[0] if videos else None


def get_video_by_manual_step(manual_step: str | None) -> dict[str, Any] | None:
    if not manual_step:
        return None
    rows = database.fetch_rows(
        "SELECT id, title, youtube_id, level, category, description, manual_step FROM videos WHERE manual_step = ?",
        (manual_step,),
    )
    return rows[0] if rows else None
