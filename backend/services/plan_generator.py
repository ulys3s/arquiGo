"""Generate architectural plan recommendations based on project preferences."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any
from .youtube_service import get_step_video

ROOM_PRESETS = {
    "cocina": {"area": 12, "type": "wet"},
    "baño": {"area": 6, "type": "wet"},
    "recámara": {"area": 14, "type": "private"},
    "patio": {"area": 10, "type": "outdoor"},
    "sala": {"area": 16, "type": "social"},
    "comedor": {"area": 12, "type": "social"},
    "área de lavado": {"area": 8, "type": "service"},
    "cochera": {"area": 18, "type": "service"},
}

PLAN_TEMPLATES = [
    {
        "name": "Proyecto A - Compacto",
        "climates": {"templado", "seco"},
        "materials": {"block", "concreto"},
        "max_levels": 2,
        "base_cost": 7800,
        "description": "Planta rectangular con patio central para ventilación.",
        "svg_template": "M10 10 H 210 V 160 H 10 Z",
    },
    {
        "name": "Proyecto B - Bioclimático",
        "climates": {"cálido", "húmedo"},
        "materials": {"madera", "adobe"},
        "max_levels": 2,
        "base_cost": 6900,
        "description": "Volúmenes escalonados con cubierta inclinada para captar lluvia.",
        "svg_template": "M10 10 H 160 L 220 90 L 160 170 H 10 Z",
    },
    {
        "name": "Proyecto C - Modular",
        "climates": {"templado", "cálido", "seco"},
        "materials": {"concreto", "block"},
        "max_levels": 2,
        "base_cost": 8400,
        "description": "Módulos flexibles que permiten ampliaciones futuras.",
        "svg_template": "M10 10 H 110 V 110 H 10 Z M130 10 H 230 V 110 H 130 Z",
    },
]

MATERIAL_COSTS = {
    "concreto": 2800,
    "block": 2400,
    "madera": 2100,
    "adobe": 1800,
}

CLIMATE_FACTORS = {
    "templado": 1.0,
    "cálido": 1.08,
    "húmedo": 1.12,
    "seco": 0.95,
}

VIABILITY_MESSAGES = [
    (0.85, "Excelente viabilidad, el proyecto puede iniciar de inmediato."),
    (0.7, "Viabilidad alta, revisa los detalles de acabados y tiempos."),
    (0.55, "Viabilidad media, considera ajustar materiales o presupuesto."),
    (0.0, "Viabilidad limitada, se recomiendan ajustes antes de construir."),
]


@dataclass
class Room:
    name: str
    area: float
    type: str


def generate_project_package(form_data: dict[str, Any]) -> dict[str, Any]:
    """Generate dashboard information based on the user's selections."""
    rooms = _build_room_program(form_data["espacios"])
    total_area = sum(room.area for room in rooms)
    blueprints = _generate_blueprints(form_data, rooms, total_area)
    materials = _estimate_materials(form_data, total_area)
    viability = _calculate_viability(form_data, rooms, materials)
    manual = _build_manual(form_data, materials)

    return {
        "overview": {
            "terrain": {
                "width": form_data["ancho_terreno"],
                "length": form_data["largo_terreno"],
                "area": form_data["ancho_terreno"] * form_data["largo_terreno"],
            },
            "family_size": form_data["personas"],
            "levels": form_data["plantas"],
            "climate": form_data["clima"],
            "material": form_data["material"],
        },
        "plans": blueprints,
        "materials": materials,
        "manual": manual,
        "viability": viability,
        "alerts": _select_alerts(form_data),
    }


def _build_room_program(selected_spaces: list[str]) -> list[Room]:
    rooms: list[Room] = []
    for space in selected_spaces:
        preset = ROOM_PRESETS.get(space.lower())
        if preset:
            rooms.append(Room(name=space.title(), area=preset["area"], type=preset["type"]))
        else:
            rooms.append(Room(name=space.title(), area=10, type="general"))
    if not rooms:
        rooms.append(Room(name="Sala-Comedor", area=28, type="social"))
    return rooms


def _generate_blueprints(
    form_data: dict[str, Any],
    rooms: list[Room],
    total_area: float,
) -> dict[str, Any]:
    options = []
    for template in PLAN_TEMPLATES:
        compatibility = _score_template(template, form_data, total_area)
        layout = _layout_rooms(rooms, form_data["ancho_terreno"], form_data["largo_terreno"])
        svg_markup = _create_svg(template["svg_template"], layout)
        options.append(
            {
                "name": template["name"],
                "description": template["description"],
                "compatibility": round(compatibility, 2),
                "blueprint_2d": {
                    "svg": svg_markup,
                    "rooms": layout,
                },
                "blueprint_3d": {
                    "volumes": _generate_volumes(layout, levels=form_data["plantas"]),
                    "render_hint": "Renderizado conceptual basado en módulos predefinidos.",
                },
            }
        )
    options.sort(key=lambda item: item["compatibility"], reverse=True)
    return {"options": options, "selected": options[0]}


def _score_template(template: dict[str, Any], form_data: dict[str, Any], total_area: float) -> float:
    score = 0.4 if form_data["clima"] in template["climates"] else 0.2
    score += 0.4 if form_data["material"] in template["materials"] else 0.15
    budget_factor = min(form_data["presupuesto"] / (template["base_cost"] * total_area), 1.2)
    score += 0.2 * min(budget_factor, 1)
    score -= 0.05 * abs(form_data["plantas"] - template["max_levels"])
    return max(0.0, min(score, 1.0))


def _layout_rooms(rooms: list[Room], width: float, length: float) -> list[dict[str, Any]]:
    grid_columns = max(2, math.ceil(math.sqrt(len(rooms))))
    cell_width = width / grid_columns
    cell_length = length / math.ceil(len(rooms) / grid_columns)
    layout = []
    for index, room in enumerate(rooms):
        column = index % grid_columns
        row = index // grid_columns
        layout.append(
            {
                "name": room.name,
                "area": room.area,
                "position": {
                    "x": round(column * cell_width, 2),
                    "y": round(row * cell_length, 2),
                },
                "dimensions": {
                    "width": round(cell_width * 0.9, 2),
                    "length": round(cell_length * 0.9, 2),
                },
            }
        )
    return layout


def _generate_volumes(layout: list[dict[str, Any]], levels: int) -> list[dict[str, Any]]:
    volumes = []
    for room in layout:
        volumes.append(
            {
                "label": room["name"],
                "footprint": room["dimensions"],
                "height": 2.8 if levels == 1 else 5.6,
            }
        )
    return volumes


def _estimate_materials(form_data: dict[str, Any], total_area: float) -> dict[str, Any]:
    material = form_data["material"]
    base_cost = MATERIAL_COSTS.get(material, 2500)
    climate_factor = CLIMATE_FACTORS.get(form_data["clima"], 1.0)
    structure_cost = total_area * base_cost * climate_factor
    finishes_cost = structure_cost * 0.25
    installations_cost = structure_cost * 0.18
    contingency = structure_cost * 0.07
    total_cost = structure_cost + finishes_cost + installations_cost + contingency

    materials = [
        {
            "name": f"{material.title()} estructural",
            "quantity": round(total_area * 1.2, 2),
            "unit": "m²",
            "unit_cost": round(base_cost, 2),
        },
        {
            "name": "Acero de refuerzo",
            "quantity": round(total_area * 0.15, 2),
            "unit": "ton",
            "unit_cost": 16500,
        },
        {
            "name": "Instalaciones hidráulicas y eléctricas",
            "quantity": round(total_area * 0.8, 2),
            "unit": "m lineales",
            "unit_cost": 480,
        },
        {
            "name": "Acabados y pintura",
            "quantity": round(total_area * 1.4, 2),
            "unit": "m²",
            "unit_cost": 220,
        },
    ]

    return {
        "items": materials,
        "estimated_total": round(total_cost, 2),
    }


def _calculate_viability(
    form_data: dict[str, Any],
    rooms: list[Room],
    materials: dict[str, Any],
) -> dict[str, Any]:
    space_factor = min(len(rooms) / (form_data["personas"] + 1), 1.2)
    budget_factor = min(form_data["presupuesto"] / max(materials["estimated_total"], 1), 1.2)
    preference_factor = 1 + 0.02 * len(form_data["preferencias"])
    score = min(space_factor * 0.4 + budget_factor * 0.4 + preference_factor * 0.2, 1.0)

    for threshold, message in VIABILITY_MESSAGES:
        if score >= threshold:
            status = message
            break
    else:
        status = VIABILITY_MESSAGES[-1][1]

    return {
        "score": round(score, 2),
        "message": status,
    }


def _build_manual(form_data: dict[str, Any], materials: dict[str, Any]) -> dict[str, Any]:
    steps = []
    levels = ["nivel_1", "nivel_2", "nivel_3", "nivel_4"]
    descriptions = {
        "nivel_1": "Preparación del terreno, trazo y cimientos con drenaje adecuado al clima.",
        "nivel_2": "Levantamiento de muros, columnas y losas principales.",
        "nivel_3": "Instalaciones eléctricas, hidráulicas y de ventilación.",
        "nivel_4": "Acabados, pintura y revisión final de seguridad.",
    }
    for idx, level in enumerate(levels, start=1):
        video = get_step_video(level)
        steps.append(
            {
                "step": idx,
                "title": f"Paso {idx}",
                "description": descriptions[level],
                "video": video,
                "materials": _materials_for_level(level, materials["items"]),
            }
        )

    return {
        "steps": steps,
        "primary_material": form_data["material"],
    }


def _materials_for_level(level: str, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if level == "nivel_1":
        return [items[0], items[1]]
    if level == "nivel_2":
        return items[:3]
    if level == "nivel_3":
        return items[2:]
    return items


def _create_svg(path: str, rooms: list[dict[str, Any]]) -> str:
    room_rects: list[str] = []
    for room in rooms:
        x = room["position"]["x"] * 10 + 20
        y = room["position"]["y"] * 10 + 20
        width = room["dimensions"]["width"] * 10
        length = room["dimensions"]["length"] * 10
        room_rects.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{width:.1f}" height="{length:.1f}" '
            "fill=\"rgba(16,185,129,0.08)\" stroke=\"#34d399\" stroke-width=\"1.5\" rx=\"6\"/>"
        )
        room_rects.append(
            f'<text x="{x + width / 2:.1f}" y="{y + length / 2:.1f}" '
            "fill=\"#d1fae5\" font-size=\"10\" text-anchor=\"middle\" dominant-baseline=\"middle\">"
            f"{room['name']}" "</text>"
        )
    svg = (
        "<svg viewBox='0 0 320 220' xmlns='http://www.w3.org/2000/svg' style='background:#020617;border-radius:18px'>"
        f"<path d='{path}' fill='rgba(15,23,42,0.6)' stroke='#64748b' stroke-width='3' />"
        + "".join(room_rects)
        + "</svg>"
    )
    return svg


def _select_alerts(form_data: dict[str, Any]) -> list[str]:
    base_alerts = marketplace.get_safety_alerts()
    alerts = base_alerts[:]
    if "accesibilidad" in form_data["necesidades"]:
        alerts.append("Asegura rampas con pendiente máxima de 8 grados y pasamanos dobles.")
    if form_data["clima"] in {"húmedo", "cálido"}:
        alerts.append("Considera ventilaciones cruzadas para evitar acumulación de humedad.")
    if form_data["material"] == "madera":
        alerts.append("Aplica tratamientos ignífugos y antihumedad en toda la madera expuesta.")
    return alerts


# Lazy import to avoid circular dependency at module level
from . import marketplace  # noqa: E402  pylint: disable=wrong-import-position
