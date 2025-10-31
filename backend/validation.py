"""Input validation utilities for API payloads."""
from __future__ import annotations

from typing import Any

ALLOWED_VALUES = {
    "presupuesto": [150000, 250000, 350000, 500000, 650000, 800000],
    "largo_terreno": [15, 18, 20, 25, 30],
    "ancho_terreno": [6, 8, 10, 12, 15],
    "ciudad": [
        "Ciudad de México",
        "Guadalajara",
        "Monterrey",
        "Mérida",
        "Puebla",
        "Querétaro",
    ],
    "localidad": [
        "Iztapalapa",
        "Tonalá",
        "Centro",
        "Cholula",
        "San Pedro",
    ],
    "clima": ["templado", "cálido", "húmedo", "seco"],
    "material": ["concreto", "block", "madera", "adobe"],
    "personas": [2, 3, 4, 5, 6, 7],
    "plantas": [1, 2, 3],
    "necesidades": [
        "accesibilidad",
        "taller",
        "negocio familiar",
        "rampa",
        "jardín",
    ],
    "preferencias": [
        "ventilación natural",
        "iluminación natural",
        "energía solar",
        "captación de agua",
        "bajo mantenimiento",
    ],
    "espacios": [
        "cocina",
        "baño",
        "recámara",
        "patio",
        "sala",
        "comedor",
        "área de lavado",
        "cochera",
        "estudio",
        "terraza",
        "baño completo",
        "recámara principal",
    ],
}

REQUIRED_FIELDS = [
    "presupuesto",
    "largo_terreno",
    "ancho_terreno",
    "ciudad",
    "localidad",
    "clima",
    "material",
    "personas",
    "plantas",
    "espacios",
]


def validate_project_payload(payload: dict[str, Any]) -> dict[str, Any]:
    errors = [field for field in REQUIRED_FIELDS if field not in payload]
    if errors:
        raise ValueError(f"Faltan campos obligatorios: {', '.join(errors)}")

    validated: dict[str, Any] = {}

    for field, allowed in ALLOWED_VALUES.items():
        if field in {"necesidades", "preferencias", "espacios"}:
            values = payload.get(field, [])
            if not isinstance(values, list):
                raise ValueError(f"El campo {field} debe ser una lista")
            invalid = [value for value in values if value not in allowed]
            if invalid:
                raise ValueError(f"Valores inválidos en {field}: {', '.join(invalid)}")
            validated[field] = values
        else:
            value = payload.get(field)
            if value not in allowed:
                raise ValueError(f"Valor inválido para {field}: {value}")
            validated[field] = value

    return validated
