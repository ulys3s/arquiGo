"""Data models used across the ConstruyeSeguro backend."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(slots=True)
class User:
    id: int
    email: str
    full_name: str | None
    city: str | None
    project_type: str | None

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "User":
        return cls(
            id=int(row["id"]),
            email=str(row["email"]),
            full_name=row.get("full_name"),
            city=row.get("city"),
            project_type=row.get("project_type"),
        )


@dataclass(slots=True)
class Project:
    id: int
    title: str
    form_data: dict[str, Any]
    plan_data: dict[str, Any]
    viability: float
    status: str
    manual_path: str | None

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "Project":
        return cls(
            id=int(row["id"]),
            title=str(row["title"]),
            form_data=row.get("form_data", {}),
            plan_data=row.get("plan_data", {}),
            viability=float(row.get("viability", 0)),
            status=str(row.get("status", "")),
            manual_path=row.get("manual_path"),
        )


@dataclass(slots=True)
class Video:
    id: int
    title: str
    url: str
    youtube_id: str
    level: str
    category: str
    stage: str | None
    manual_step: str | None
    description: str | None
    embed_url: str
    thumbnail_url: str | None

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "Video":
        youtube_id = str(row["youtube_id"])
        return cls(
            id=int(row["id"]),
            title=str(row["title"]),
            url=build_youtube_watch_url(youtube_id),
            youtube_id=youtube_id,
            level=str(row.get("level", "principiante")),
            category=str(row.get("category", "")),
            stage=row.get("stage"),
            manual_step=row.get("manual_step"),
            description=row.get("description"),
            embed_url=build_youtube_embed_url(youtube_id),
            thumbnail_url=build_youtube_thumbnail_url(youtube_id),
        )


@dataclass(slots=True)
class Provider:
    id: int
    name: str
    provider_type: str
    specialty: str | None
    city: str
    locality: str | None
    price_min: float | None
    price_max: float | None
    rating: float | None
    description: str | None
    contact: str | None
    portfolio_url: str | None
    experience_years: int | None

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "Provider":
        return cls(
            id=int(row["id"]),
            name=str(row["name"]),
            provider_type=str(row.get("provider_type", "")),
            specialty=row.get("specialty"),
            city=str(row.get("city", "")),
            locality=row.get("locality"),
            price_min=_to_float(row.get("price_min")),
            price_max=_to_float(row.get("price_max")),
            rating=_to_float(row.get("rating")),
            description=row.get("description"),
            contact=row.get("contact"),
            portfolio_url=row.get("portfolio_url"),
            experience_years=_to_int(row.get("experience_years")),
        )


def _to_float(value: Any) -> float | None:
    try:
        return None if value is None else float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: Any) -> int | None:
    try:
        return None if value is None else int(value)
    except (TypeError, ValueError):
        return None


def build_youtube_watch_url(youtube_id: str) -> str:
    """Return a YouTube URL that works for videos and playlists."""

    if youtube_id.startswith("videoseries?list="):
        list_id = youtube_id.split("list=", 1)[1]
        return f"https://www.youtube.com/playlist?list={list_id}"
    return f"https://www.youtube.com/watch?v={youtube_id}"


def build_youtube_embed_url(youtube_id: str) -> str:
    """Return an embeddable URL that keeps branding to a minimum."""

    base = f"https://www.youtube.com/embed/{youtube_id}"
    separator = "&" if "?" in youtube_id else "?"
    return f"{base}{separator}rel=0&modestbranding=1"


def build_youtube_thumbnail_url(youtube_id: str) -> str | None:
    """Return a thumbnail URL when available for the given YouTube resource."""

    if youtube_id.startswith("videoseries?list="):
        return None
    return f"https://img.youtube.com/vi/{youtube_id}/hqdefault.jpg"
