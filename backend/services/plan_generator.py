"""Generate architectural plan recommendations based on project preferences."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from .youtube_service import get_step_video, get_video_by_manual_step

ROOM_PRESETS = {
    "cocina": {"area": 12, "type": "wet"},
    "baño": {"area": 6, "type": "wet"},
    "baño completo": {"area": 7, "type": "wet"},
    "recámara": {"area": 14, "type": "private"},
    "recámara principal": {"area": 18, "type": "private"},
    "patio": {"area": 10, "type": "outdoor"},
    "sala": {"area": 16, "type": "social"},
    "comedor": {"area": 12, "type": "social"},
    "estudio": {"area": 9, "type": "social"},
    "área de lavado": {"area": 8, "type": "service"},
    "cochera": {"area": 18, "type": "service"},
    "terraza": {"area": 14, "type": "outdoor"},
}

ROOM_GUIDES = {
    "cocina": "acabados_finales",
    "baño": "instalaciones_seguras",
    "baño completo": "instalaciones_seguras",
    "recámara": "levantamiento_muros",
    "recámara principal": "levantamiento_muros",
    "patio": "ventilacion_iluminacion",
    "sala": "levantamiento_muros",
    "comedor": "levantamiento_muros",
    "estudio": "levantamiento_muros",
    "área de lavado": "preparacion_terreno",
    "cochera": "preparacion_terreno",
    "terraza": "ventilacion_iluminacion",
}

PLAN_TEMPLATES = [
    {
        "name": "Proyecto A - Compacto",
        "climates": {"templado", "seco"},
        "materials": {"block", "concreto"},
        "max_levels": 2,
        "base_cost": 7800,
        "description": "Planta rectangular con patio central para ventilación.",
        "svg_template": "M20 20 H 300 V 200 H 20 Z",
    },
    {
        "name": "Proyecto B - Bioclimático",
        "climates": {"cálido", "húmedo"},
        "materials": {"madera", "adobe"},
        "max_levels": 2,
        "base_cost": 6900,
        "description": "Volúmenes escalonados con cubierta inclinada para captar lluvia.",
        "svg_template": "M30 40 H 200 L 280 120 L 200 200 H 30 Z",
    },
    {
        "name": "Proyecto C - Modular",
        "climates": {"templado", "cálido", "seco"},
        "materials": {"concreto", "block"},
        "max_levels": 3,
        "base_cost": 8400,
        "description": "Módulos flexibles que permiten ampliaciones futuras.",
        "svg_template": "M20 20 H 160 V 120 H 20 Z M190 20 H 330 V 180 H 190 Z",
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

PREFERENCE_WEIGHTS = {
    "ventilación natural": 0.05,
    "iluminación natural": 0.05,
    "energía solar": 0.03,
    "captación de agua": 0.02,
}

VIABILITY_MESSAGES = [
    (0.85, "Excelente viabilidad, el proyecto puede iniciar de inmediato."),
    (0.7, "Viabilidad alta, revisa los detalles de acabados y tiempos."),
    (0.55, "Viabilidad media, considera ajustar materiales o presupuesto."),
    (0.0, "Viabilidad limitada, se recomiendan ajustes antes de construir."),
]

SITE_COORDINATES = {
    ("ciudad de méxico", "iztapalapa"): {"lat": 19.3579, "lng": -99.0671, "solar": "El sol nace por oriente con sombras hacia poniente al atardecer."},
    ("guadalajara", "tonalá"): {"lat": 20.624, "lng": -103.233, "solar": "Aprovecha la luz matutina orientando áreas sociales al este."},
    ("puebla", "cholula"): {"lat": 19.0552, "lng": -98.3003, "solar": "Las tardes son soleadas, considera aleros hacia el oeste."},
}


@dataclass
class Room:
    name: str
    area: float
    type: str
    guide: str | None = None


def generate_project_package(form_data: dict[str, Any]) -> dict[str, Any]:
    """Generate dashboard information based on the user's selections."""
    rooms = _build_room_program(form_data.get("espacios", []))
    total_area = sum(room.area for room in rooms)
    site = _build_site_profile(form_data)
    blueprints = _generate_blueprints(form_data, rooms, total_area, site)
    materials = _estimate_materials(form_data, total_area)
    viability = _calculate_viability(form_data, rooms, materials)
    manual = _build_manual(form_data, materials)

    return {
        "overview": {
            "terrain": {
                "width": form_data.get("ancho_terreno", 0),
                "length": form_data.get("largo_terreno", 0),
                "area": form_data.get("ancho_terreno", 0) * form_data.get("largo_terreno", 0),
            },
            "family_size": form_data.get("personas", 1),
            "levels": form_data.get("plantas", 1),
            "climate": form_data.get("clima"),
            "material": form_data.get("material"),
            "preferences": form_data.get("preferencias", []),
            "city": form_data.get("ciudad"),
            "locality": form_data.get("localidad"),
        },
        "site": site,
        "plans": blueprints,
        "materials": materials,
        "manual": manual,
        "viability": viability,
        "alerts": _select_alerts(form_data),
    }


def _build_room_program(selected_spaces: list[str]) -> list[Room]:
    rooms: list[Room] = []
    for space in selected_spaces:
        normalized = space.lower()
        preset = ROOM_PRESETS.get(normalized)
        guide = ROOM_GUIDES.get(normalized)
        if preset:
            rooms.append(
                Room(name=space.title(), area=preset["area"], type=preset["type"], guide=guide)
            )
        else:
            rooms.append(Room(name=space.title(), area=10, type="general", guide=guide))
    if not rooms:
        rooms.append(Room(name="Sala-Comedor", area=28, type="social", guide="levantamiento_muros"))
    return rooms


def _generate_blueprints(
    form_data: dict[str, Any],
    rooms: list[Room],
    total_area: float,
    site: dict[str, Any],
) -> dict[str, Any]:
    options = []
    for template in PLAN_TEMPLATES:
        compatibility = _score_template(template, form_data, total_area)
        layout = _layout_rooms(rooms, form_data.get("ancho_terreno", 0), form_data.get("largo_terreno", 0))
        svg_markup = _create_svg(template["svg_template"], layout)
        options.append(
            {
                "name": template["name"],
                "description": template["description"],
                "compatibility": round(compatibility, 2),
                "blueprint_2d": {
                    "svg": svg_markup,
                    "rooms": layout,
                    "legend": _build_room_legend(layout),
                },
                "blueprint_3d": {
                    "volumes": _generate_volumes(layout, levels=form_data["plantas"]),
                    "render_hint": "Renderizado conceptual basado en módulos predefinidos.",
                },
                "solar_orientation": site.get("solar"),
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
        color = _room_color(room.type)
        guide_video = get_video_by_manual_step(room.guide) if room.guide else None
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
                "style": {
                    "fill": color,
                    "stroke": "#1f2937",
                    "text": "#0f172a",
                },
                "guide": {
                    "manual_step": room.guide,
                    "video": guide_video,
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
    preference_factor = 1
    for preference in form_data.get("preferencias", []):
        preference_factor += PREFERENCE_WEIGHTS.get(preference.lower(), 0.01)
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
    levels = ["principiante", "intermedio", "avanzado"]
    descriptions = {
        "principiante": "Preparación del terreno, trazo y cimentación con drenajes adecuados.",
        "intermedio": "Levantamiento de muros, instalaciones básicas y losas ligeras.",
        "avanzado": "Acabados, impermeabilización y checklist final de seguridad.",
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
    if level == "principiante":
        return items[:2]
    if level == "intermedio":
        return items[:3]
    return items


def _create_svg(path: str, rooms: list[dict[str, Any]]) -> str:
    grid_lines = []
    for offset in range(20, 340, 20):
        grid_lines.append(
            f"<line x1='{offset}' y1='20' x2='{offset}' y2='220' stroke='rgba(148,163,184,0.2)' stroke-width='0.5' />"
        )
        grid_lines.append(
            f"<line x1='20' y1='{offset}' x2='340' y2='{offset}' stroke='rgba(148,163,184,0.2)' stroke-width='0.5' />"
        )

    room_rects: list[str] = []
    for room in rooms:
        x = room["position"]["x"] * 10 + 20
        y = room["position"]["y"] * 10 + 20
        width = room["dimensions"]["width"] * 10
        length = room["dimensions"]["length"] * 10
        room_rects.append(
            f"<g class='room' data-room='{room['name']}'>"
            f"<rect x='{x:.1f}' y='{y:.1f}' width='{width:.1f}' height='{length:.1f}' rx='10' ry='10'"
            f" fill='{room['style']['fill']}' stroke='{room['style']['stroke']}' stroke-width='2' />"
            f"<text x='{x + width / 2:.1f}' y='{y + length / 2:.1f}' fill='{room['style']['text']}'"
            " font-size='11' font-family='Inter, sans-serif' text-anchor='middle' dominant-baseline='middle'>"
            f"{room['name']}" "</text>"
            "</g>"
        )
    svg = (
        "<svg viewBox='0 0 360 240' xmlns='http://www.w3.org/2000/svg'"
        " style='background:#f8fafc;border-radius:18px;box-shadow:0 20px 45px rgba(15,23,42,0.18)'>"
        "<defs><style>.room:hover{cursor:pointer;opacity:0.92;}</style></defs>"
        + "".join(grid_lines)
        + f"<path d='{path}' fill='rgba(148,163,184,0.15)' stroke='#0f172a' stroke-width='3' />"
        + "".join(room_rects)
        + "</svg>"
    )
    return svg


def _room_color(room_type: str) -> str:
    palette = {
        "wet": "#bae6fd",
        "private": "#c7d2fe",
        "social": "#bbf7d0",
        "service": "#fde68a",
        "outdoor": "#fbcfe8",
        "general": "#e0f2fe",
    }
    return palette.get(room_type, "#e2e8f0")


def _build_room_legend(rooms: list[dict[str, Any]]) -> list[dict[str, str]]:
    legend = []
    for room in rooms:
        legend.append(
            {
                "name": room["name"],
                "type": room.get("guide", {}).get("manual_step"),
                "color": room["style"]["fill"],
            }
        )
    return legend


def _build_site_profile(form_data: dict[str, Any]) -> dict[str, Any]:
    city = (form_data.get("ciudad") or "").lower()
    locality = (form_data.get("localidad") or "").lower()
    coordinates = SITE_COORDINATES.get((city, locality))
    if coordinates is None:
        coordinates = {"lat": 19.4326, "lng": -99.1332, "solar": "Orientar áreas sociales al sur optimiza el asoleamiento."}
    preferences = [value.lower() for value in form_data.get("preferencias", [])]
    recommendations = [
        "Delimita la zona de construcción con estacas y cuerdas para proteger al vecindario.",
        "Respeta retiros frontales y laterales según el reglamento local.",
    ]
    if "ventilación natural" in preferences:
        recommendations.append("Integra aperturas cruzadas en sala y comedor para ventilación continua.")
    if "iluminación natural" in preferences:
        recommendations.append("Añade domos o tragaluces en áreas de circulación para reducir consumo eléctrico.")
    return {
        "coordinates": {"lat": coordinates["lat"], "lng": coordinates["lng"]},
        "solar": coordinates["solar"],
        "recommendations": recommendations,
        "city": form_data.get("ciudad"),
        "locality": form_data.get("localidad"),
    }


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
