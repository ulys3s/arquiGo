"""Utility helpers to integrate YouTube content."""
from __future__ import annotations

from typing import Any, Iterable, Sequence

from .. import database
from ..models import build_youtube_embed_url, build_youtube_watch_url


LEVEL_ALIASES = {
    "principiante": "cimientos",
    "intermedio": "estructura",
    "avanzado": "acabados",
}

STAGE_KEYWORDS: dict[str, set[str]] = {
    "Preparación del terreno y cimientos": {"cimientos", "preparacion_terreno"},
    "Muros y estructura": {"estructura", "levantamiento_muros"},
    "Instalaciones hidráulicas y eléctricas": {"instalaciones", "instalaciones_seguras"},
    "Acabados, pintura y techumbre": {"acabados", "acabados_finales"},
    "Ventilación, iluminación y confort": {"ventilacion", "ventilacion_iluminacion"},
}

STAGE_ORDER: Sequence[str] = tuple(STAGE_KEYWORDS.keys())
DEFAULT_STAGE = "Aprendizaje complementario"


def list_videos(
    *,
    category: str | None = None,
    search: str | None = None,
    level: str | None = None,
) -> list[dict[str, Any]]:
    """Return videos from the catalog filtered by category, level or keyword."""

    videos = database.list_videos(category=category, level=level, search=search)
    for video in videos:
        if not video.get("stage"):
            video["stage"] = _stage_for_video(video)
        video.setdefault("tags", "")
        _enrich_video(video)
    videos.sort(key=_video_sort_key)
    return videos


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
    for video in list_videos():
        if (video.get("manual_step") or "").lower() == manual_step.lower():
            return video
    return None


def group_videos_by_stage() -> dict[str, list[dict[str, Any]]]:
    """Return all catalogued videos grouped by learning stage."""
    grouped: dict[str, list[dict[str, Any]]] = {stage: [] for stage in STAGE_ORDER}
    grouped[DEFAULT_STAGE] = []
    for video in list_videos():
        grouped.setdefault(video["stage"], []).append(video)
    return grouped


def recommended_videos_for_project(
    form_data: dict[str, Any],
    watched_ids: Iterable[int] | None = None,
) -> list[dict[str, Any]]:
    """Build a playlist tailored to the project configuration."""

    watched = set(watched_ids or [])
    priority_targets: set[str] = set()
    levels = int(form_data.get("plantas") or 1)
    spaces = {space.lower() for space in form_data.get("espacios", [])}
    preferences = {pref.lower() for pref in form_data.get("preferencias", [])}
    climate = (form_data.get("clima") or "").lower()
    orientation = (form_data.get("orientacion") or "").lower()
    ventilation = (form_data.get("ventilacion") or "").lower()
    lighting = (form_data.get("iluminacion") or "").lower()

    if levels > 1:
        priority_targets.add("levantamiento_muros")
    if any("baño" in space for space in spaces) or "baño exterior" in preferences:
        priority_targets.add("instalaciones_seguras")
    if "terraza" in spaces or "ventilación natural" in preferences or "iluminación natural" in preferences:
        priority_targets.add("ventilacion_iluminacion")
    if "energía solar" in preferences or "captación de agua" in preferences:
        priority_targets.add("preparacion_terreno")
    if climate in {"húmedo", "humedo"}:
        priority_targets.update({"drenaje", "impermeabilizacion", "preparacion_terreno"})
    if orientation:
        priority_targets.add("orientacion")
    if ventilation:
        priority_targets.add("ventilacion")
    if lighting:
        priority_targets.add("iluminacion")
    if "cochera" in spaces:
        priority_targets.add("cochera")
    if "patio" in spaces:
        priority_targets.add("drenaje")

    grouped = group_videos_by_stage()
    playlist: list[dict[str, Any]] = []
    for stage in STAGE_ORDER:
        videos = grouped.get(stage, [])
        if not videos:
            continue
        curated = _prioritize_videos(videos, priority_targets, watched)
        playlist.append({"stage": stage, "videos": curated})

    extras = grouped.get(DEFAULT_STAGE, [])
    if extras:
        curated = _prioritize_videos(extras, priority_targets, watched, limit=2)
        if curated:
            playlist.append({"stage": DEFAULT_STAGE, "videos": curated})
    return playlist


def recommended_videos_for_user(
    user: dict[str, Any],
    projects: list[dict[str, Any]],
    watched_ids: Iterable[int] | None,
) -> list[dict[str, Any]]:
    """Return a playlist taking the user's last project as reference."""

    if projects:
        reference = projects[0].get("form_data") or {}
    else:
        reference = {
            "plantas": 1,
            "espacios": [],
            "preferencias": [],
            "ciudad": user.get("city"),
        }
    return recommended_videos_for_project(reference, watched_ids=watched_ids)


def _enrich_video(video: dict[str, Any]) -> dict[str, Any]:
    youtube_id = str(video.get("youtube_id", ""))
    video["url"] = build_youtube_watch_url(youtube_id)
    video["watch_url"] = video["url"]
    video["embed_url"] = build_youtube_embed_url(youtube_id)
    return video


def _stage_for_video(video: dict[str, Any]) -> str:
    manual_step = (video.get("manual_step") or "").lower()
    category = (video.get("category") or "").lower()
    for stage, keywords in STAGE_KEYWORDS.items():
        if manual_step in keywords or category in keywords:
            return stage
    return DEFAULT_STAGE


def _video_sort_key(video: dict[str, Any]) -> tuple[int, str]:
    stage_index = STAGE_ORDER.index(video["stage"]) if video["stage"] in STAGE_ORDER else len(STAGE_ORDER)
    return (stage_index, video.get("title", ""))


def _video_targets(video: dict[str, Any]) -> set[str]:
    manual_step = (video.get("manual_step") or "").lower()
    tags = {manual_step} if manual_step else set()
    raw_tags = video.get("tags") or ""
    for tag in raw_tags.split(","):
        tag = tag.strip().lower()
        if tag:
            tags.add(tag)
    return {tag for tag in tags if tag}


def _prioritize_videos(
    videos: list[dict[str, Any]],
    priority_targets: set[str],
    watched_ids: set[int],
    *,
    limit: int = 3,
) -> list[dict[str, Any]]:
    def sort_key(video: dict[str, Any]) -> tuple[int, int, str]:
        targets = _video_targets(video)
        priority_score = 0 if targets & priority_targets else 1
        watched_score = 0 if video.get("id") not in watched_ids else 1
        return (priority_score, watched_score, video.get("title", ""))

    ordered = sorted(videos, key=sort_key)
    return ordered[:limit]
