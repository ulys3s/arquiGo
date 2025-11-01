"""Seed script to populate the ConstruyeSeguro video library."""
from __future__ import annotations

from backend import database
from backend.data.video_catalog import VIDEO_CATALOG


def main() -> None:
    database.init_db()
    with database.get_connection() as connection:
        connection.execute("DELETE FROM video_watch_history")
        connection.execute("DELETE FROM videos")
        for video in VIDEO_CATALOG:
            connection.execute(
                """
                INSERT INTO videos (title, category, youtube_id, level, stage, description, manual_step, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    video["title"],
                    video["category"],
                    video["youtube_id"],
                    video["level"],
                    video["stage"],
                    video["description"],
                    video["manual_step"],
                    video.get("tags", ""),
                ),
            )
    print("Catálogo de videos actualizado correctamente.")


if __name__ == "__main__":
    main()
