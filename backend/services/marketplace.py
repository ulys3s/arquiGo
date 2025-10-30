"""Marketplace helpers for ConstruyeSeguro."""
from __future__ import annotations

from typing import Any

from .. import database

SAFETY_ALERTS = [
    "No uses cemento húmedo o caducado durante la mezcla.",
    "Mantén los pasillos de obra libres de escombros para evitar accidentes.",
    "Verifica la resistencia del suelo antes de vaciar losas o cimentaciones.",
    "Deja claros los vanos para ventilación natural en cada espacio habitable.",
]


def get_architects(city: str | None = None, specialty: str | None = None) -> list[dict[str, Any]]:
    query = "SELECT name, specialty, price_range, city, portfolio_url, rating FROM architects"
    params: list[str] = []
    filters: list[str] = []

    if city:
        filters.append("city = ?")
        params.append(city)
    if specialty:
        filters.append("specialty = ?")
        params.append(specialty)

    if filters:
        query += " WHERE " + " AND ".join(filters)

    query += " ORDER BY rating DESC"
    return database.fetch_rows(query, params)


def get_suppliers(city: str | None = None, material: str | None = None) -> list[dict[str, Any]]:
    query = (
        "SELECT name, address, city, contact, material_focus, latitude, longitude, rating FROM suppliers"
    )
    params: list[str] = []
    filters: list[str] = []

    if city:
        filters.append("city = ?")
        params.append(city)
    if material:
        filters.append("material_focus LIKE ?")
        params.append(f"%{material}%")

    if filters:
        query += " WHERE " + " AND ".join(filters)

    query += " ORDER BY rating DESC"
    return database.fetch_rows(query, params)


def get_safety_alerts() -> list[str]:
    return SAFETY_ALERTS


def get_supplier_markers(city: str | None = None, material: str | None = None) -> list[dict[str, Any]]:
    markers = []
    for supplier in get_suppliers(city=city, material=material):
        if supplier["latitude"] is None or supplier["longitude"] is None:
            continue
        markers.append(
            {
                "name": supplier["name"],
                "lat": supplier["latitude"],
                "lng": supplier["longitude"],
                "material": supplier["material_focus"],
                "city": supplier["city"],
            }
        )
    return markers
