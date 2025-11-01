"""Generate architectural plan recommendations based on project preferences."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from .youtube_service import (
    get_step_video,
    get_video_by_manual_step,
    recommended_videos_for_project,
)

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
    manual["recommended_videos"] = recommended_videos_for_project(form_data)

    return {
        "overview": {
            "terrain": {
                "width": form_data.get("ancho_terreno", 0),
                "length": form_data.get("largo_terreno", 0),
                "area": form_data.get("ancho_terreno", 0) * form_data.get("largo_terreno", 0),
                "boundary": form_data.get("boundary"),
            },
            "family_size": form_data.get("personas", 1),
            "levels": form_data.get("plantas", 1),
            "climate": form_data.get("clima"),
            "material": form_data.get("material"),
            "preferences": form_data.get("preferencias", []),
            "city": form_data.get("ciudad"),
            "locality": form_data.get("localidad"),
            "orientation": form_data.get("orientacion"),
            "ventilation": form_data.get("ventilacion"),
            "lighting": form_data.get("iluminacion"),
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
        layout, metrics = _layout_rooms(
            rooms,
            form_data.get("ancho_terreno", 0),
            form_data.get("largo_terreno", 0),
            orientation=form_data.get("orientacion"),
        )
        svg_markup, svg_meta = _create_svg(template["svg_template"], layout, metrics, form_data)
        options.append(
            {
                "name": template["name"],
                "description": template["description"],
                "compatibility": round(compatibility, 2),
                "blueprint_2d": {
                    "svg": svg_markup,
                    "rooms": layout,
                    "legend": _build_room_legend(layout),
                    "scale": svg_meta["scale_label"],
                    "orientation": svg_meta["orientation"],
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


def _layout_rooms(
    rooms: list[Room],
    width: float,
    length: float,
    *,
    orientation: str | None = None,
) -> tuple[list[dict[str, Any]], dict[str, float]]:
    orientation = (orientation or "norte").lower()
    total_area = sum(room.area for room in rooms)
    envelope_width = max(width - 1.2, math.sqrt(total_area) * 0.9, 6.0)
    envelope_length = max(length - 1.2, total_area / max(envelope_width, 1.0), 6.0)
    corridor = 0.8
    max_width = envelope_width - corridor
    x_cursor = 0.0
    y_cursor = 0.0
    row_height = 0.0
    total_width = 0.0
    total_length = 0.0
    layout: list[dict[str, Any]] = []

    order = {"social": 0, "service": 1, "wet": 2, "private": 3, "outdoor": 4, "general": 5}
    sorted_rooms = sorted(rooms, key=lambda item: order.get(item.type, 99))

    for room in sorted_rooms:
        target_area = max(room.area, 6.0)
        aspect_ratio = 1.35 if room.type in {"private", "wet"} else 1.15
        width_guess = max(round(math.sqrt(target_area / aspect_ratio), 2), 2.6)
        length_guess = max(round(target_area / width_guess, 2), 2.6)

        if x_cursor + width_guess > max_width and x_cursor > 0:
            x_cursor = 0.0
            y_cursor += row_height + corridor
            row_height = 0.0

        width_guess = min(width_guess, max_width - x_cursor if max_width - x_cursor > 2.4 else width_guess)
        length_guess = max(round(target_area / max(width_guess, 2.4), 2), 2.6)

        position_x = round(corridor / 2 + x_cursor, 2)
        position_y = round(corridor / 2 + y_cursor, 2)

        x_cursor += width_guess + corridor
        row_height = max(row_height, length_guess)
        total_width = max(total_width, x_cursor)
        total_length = max(total_length, y_cursor + length_guess + corridor)

        color = _room_color(room.type)
        guide_video = get_video_by_manual_step(room.guide) if room.guide else None
        base_font_size = max(12, min(22, int(min(width_guess, length_guess) * 5.2)))

        layout.append(
            {
                "name": room.name,
                "area": round(target_area, 1),
                "position": {"x": position_x, "y": position_y},
                "dimensions": {"width": round(width_guess, 2), "length": round(length_guess, 2)},
                "style": {
                    "fill": color,
                    "stroke": "#0f172a",
                    "text": "#0f172a",
                    "font_size": base_font_size,
                },
                "labels": {
                    "dimensions": f"{width_guess:.1f}m × {length_guess:.1f}m",
                },
                "guide": {"manual_step": room.guide, "video": guide_video},
                "openings": {
                    "doors": [
                        {
                            "side": "sur",
                            "offset": round(width_guess / 2, 2),
                            "width": round(max(width_guess * 0.35, 0.9), 2),
                        }
                    ],
                    "windows": [
                        {
                            "side": "norte",
                            "offset": round(width_guess / 2, 2),
                            "width": round(max(width_guess * 0.45, 1.0), 2),
                        }
                    ],
                },
                "orientation": orientation,
                "room_type": room.type,
            }
        )

    metrics = {
        "width": round(max(total_width, envelope_width), 2),
        "length": round(max(total_length, y_cursor + row_height + corridor, envelope_length), 2),
        "corridor": corridor,
        "envelope_width": round(envelope_width, 2),
    }
    return layout, metrics


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


def _create_svg(
    path: str,
    rooms: list[dict[str, Any]],
    metrics: dict[str, float],
    form_data: dict[str, Any],
) -> tuple[str, dict[str, str]]:
    orientation = (form_data.get("orientacion") or "norte").lower()
    orientation_angles = {"norte": 0, "este": 90, "sur": 180, "oeste": 270}
    north_rotation = orientation_angles.get(orientation, 0)
    width_m = max(metrics.get("width", 8.0), 6.0)
    length_m = max(metrics.get("length", 8.0), 6.0)
    px_per_meter = 37.8
    width_px = width_m * px_per_meter
    length_px = length_m * px_per_meter
    margin_x = 96
    margin_y = 120
    view_width = width_px + margin_x * 2 + 260
    view_height = length_px + margin_y * 2 + 280

    grid_lines: list[str] = []
    for offset in range(0, int(width_m) + 1):
        x = margin_x + offset * px_per_meter
        grid_lines.append(
            f"<line x1='{x:.1f}' y1='{margin_y:.1f}' x2='{x:.1f}' y2='{margin_y + length_px:.1f}' stroke='rgba(148,163,184,0.16)' stroke-width='0.7' />"
        )
    for offset in range(0, int(length_m) + 1):
        y = margin_y + offset * px_per_meter
        grid_lines.append(
            f"<line x1='{margin_x:.1f}' y1='{y:.1f}' x2='{margin_x + width_px:.1f}' y2='{y:.1f}' stroke='rgba(148,163,184,0.16)' stroke-width='0.7' />"
        )

    pattern_defs = (
        "<pattern id='hatch-outdoor' patternUnits='userSpaceOnUse' width='18' height='18' patternTransform='rotate(45)'>"
        "<rect width='18' height='18' fill='rgba(56,189,248,0.16)'/>"
        "<path d='M0 9 H18' stroke='rgba(14,116,144,0.35)' stroke-width='2'/>"
        "</pattern>"
        "<pattern id='hatch-service' patternUnits='userSpaceOnUse' width='16' height='16' patternTransform='rotate(45)'>"
        "<rect width='16' height='16' fill='rgba(251,191,36,0.14)'/>"
        "<path d='M0 8 H16' stroke='rgba(217,119,6,0.35)' stroke-width='2'/>"
        "</pattern>"
    )

    room_layers: list[str] = []
    for room in rooms:
        x = margin_x + room["position"]["x"] * px_per_meter
        y = margin_y + room["position"]["y"] * px_per_meter
        width = room["dimensions"]["width"] * px_per_meter
        length = room["dimensions"]["length"] * px_per_meter
        font_size = room["style"].get("font_size", 14)
        room_type = room.get("room_type")
        fill_color = room["style"].get("fill", "#e2e8f0")
        stroke_color = room["style"].get("stroke", "#0f172a")
        text_color = room["style"].get("text", "#0f172a")
        fill_opacity = 0.9 if room_type not in {"outdoor"} else 0.78
        stroke_width = 3.4 if room_type not in {"outdoor"} else 2.6
        hatch_id = "hatch-outdoor" if room_type == "outdoor" else "hatch-service" if room_type == "service" else None

        door_layers: list[str] = []
        for door in room.get("openings", {}).get("doors", []):
            door_width_px = door["width"] * px_per_meter
            if door["side"] == "sur":
                door_x = x + max(door["offset"] * px_per_meter - door_width_px / 2, 12)
                door_y = y + length
                door_layers.append(
                    f"<path d='M{door_x:.1f},{door_y:.1f} h{door_width_px:.1f}' stroke='#f97316' stroke-width='4' stroke-linecap='round'/>"
                )
            elif door["side"] == "norte":
                door_x = x + max(door["offset"] * px_per_meter - door_width_px / 2, 12)
                door_layers.append(
                    f"<path d='M{door_x:.1f},{y:.1f} h{door_width_px:.1f}' stroke='#f97316' stroke-width='4' stroke-linecap='round'/>"
                )

        window_layers: list[str] = []
        for window in room.get("openings", {}).get("windows", []):
            window_width_px = window["width"] * px_per_meter
            if window["side"] == "norte":
                win_x = x + max(window["offset"] * px_per_meter - window_width_px / 2, 12)
                window_layers.append(
                    f"<rect x='{win_x:.1f}' y='{y - 6:.1f}' width='{window_width_px:.1f}' height='6' fill='rgba(59,130,246,0.35)' stroke='#3b82f6' stroke-dasharray='8 6' />"
                )
            elif window["side"] == "este":
                win_y = y + max(window["offset"] * px_per_meter - window_width_px / 2, 12)
                window_layers.append(
                    f"<rect x='{x + width - 6:.1f}' y='{win_y:.1f}' width='6' height='{window_width_px:.1f}' fill='rgba(59,130,246,0.35)' stroke='#3b82f6' stroke-dasharray='8 6' />"
                )

        max_chars = max(
            10,
            min(18, int(min(room["dimensions"]["width"], room["dimensions"]["length"]) * 3.4)),
        )
        label_lines = _wrap_label(room["name"], max_chars)
        line_height = max(font_size + 2, 14)
        while True:
            block_height = line_height * len(label_lines)
            label_start_y = y + length / 2 - (block_height - line_height) / 2
            dims_y = label_start_y + block_height + 6
            if dims_y <= y + length - 10 or font_size <= 12:
                break
            font_size -= 1
            line_height = max(font_size + 2, 13)
        dims_font = max(font_size - 2, 11)
        dims_y = min(dims_y, y + length - 10)
        center_x = x + width / 2

        name_markup = (
            f"<text x='{center_x:.1f}' y='{label_start_y:.1f}' fill='{text_color}' font-size='{font_size}' "
            "font-family='Inter, sans-serif' font-weight='600' text-anchor='middle'>"
            + "".join(
                f"<tspan x='{center_x:.1f}' dy='{0 if index == 0 else line_height:.1f}'>{line}</tspan>"
                for index, line in enumerate(label_lines)
            )
            + "</text>"
        )
        dims_markup = (
            f"<text x='{center_x:.1f}' y='{dims_y:.1f}' fill='#475569' font-size='{dims_font}' font-family='Inter, sans-serif' text-anchor='middle'>"
            f"{room['area']} m² · {room['labels']['dimensions']}"
            "</text>"
        )

        hatch_overlay = (
            f"<rect x='{x:.1f}' y='{y:.1f}' width='{width:.1f}' height='{length:.1f}' rx='18' ry='18' fill='url(#{hatch_id})' fill-opacity='0.55' />"
            if hatch_id
            else ""
        )

        room_layers.append(
            f"<g class='room' data-room='{room['name']}'>"
            f"<rect x='{x:.1f}' y='{y:.1f}' width='{width:.1f}' height='{length:.1f}' rx='18' ry='18' fill='{fill_color}' fill-opacity='{fill_opacity}' stroke='{stroke_color}' stroke-width='{stroke_width}' />"
            f"{hatch_overlay}"
            + "".join(door_layers)
            + "".join(window_layers)
            + name_markup
            + dims_markup
            + "</g>"
        )

    dimension_lines = (
        f"<line x1='{margin_x:.1f}' y1='{margin_y + length_px + 36:.1f}' x2='{margin_x + width_px:.1f}' y2='{margin_y + length_px + 36:.1f}' stroke='#94a3b8' stroke-width='1.6' marker-start='url(#arrow)' marker-end='url(#arrow)' />"
        + f"<text x='{margin_x + width_px / 2:.1f}' y='{margin_y + length_px + 58:.1f}' fill='#475569' font-size='13' font-family='Inter, sans-serif' text-anchor='middle'>{width_m:.1f} m</text>"
        + f"<line x1='{margin_x - 36:.1f}' y1='{margin_y:.1f}' x2='{margin_x - 36:.1f}' y2='{margin_y + length_px:.1f}' stroke='#94a3b8' stroke-width='1.6' marker-start='url(#arrow)' marker-end='url(#arrow)' />"
        + f"<text x='{margin_x - 58:.1f}' y='{margin_y + length_px / 2:.1f}' fill='#475569' font-size='13' font-family='Inter, sans-serif' text-anchor='middle' transform='rotate(-90 {margin_x - 58:.1f} {margin_y + length_px / 2:.1f})'>{length_m:.1f} m</text>"
    )

    scale_label = _build_scale_label(width_m, length_m)
    segment = 5 if width_m >= 12 else 3 if width_m >= 9 else 2
    scale_bar = (
        "<g transform='translate("
        + f"{margin_x:.1f},{margin_y + length_px + 100:.1f})' fill='none' stroke='#0f172a' stroke-width='2.4'>"
        + f"<rect width='{segment * px_per_meter:.1f}' height='12' fill='#0f172a' rx='3' />"
        + f"<rect x='{segment * px_per_meter:.1f}' width='{segment * px_per_meter:.1f}' height='12' fill='#38bdf8' rx='3' />"
        + f"<rect x='{segment * 2 * px_per_meter:.1f}' width='{segment * px_per_meter:.1f}' height='12' fill='#0f172a' opacity='0.8' rx='3' />"
        + f"<text x='0' y='32' fill='#334155' font-size='12' font-family='Inter, sans-serif'>0 m</text>"
        + f"<text x='{segment * px_per_meter:.1f}' y='32' fill='#334155' font-size='12' font-family='Inter, sans-serif' text-anchor='middle'>{segment} m</text>"
        + f"<text x='{segment * 2 * px_per_meter:.1f}' y='32' fill='#334155' font-size='12' font-family='Inter, sans-serif' text-anchor='middle'>{segment * 2} m</text>"
        + f"<text x='{segment * 3 * px_per_meter:.1f}' y='32' fill='#334155' font-size='12' font-family='Inter, sans-serif' text-anchor='end'>{segment * 3} m</text>"
        + f"<text x='0' y='52' fill='#0f172a' font-weight='600' font-size='13' font-family='Inter, sans-serif'>{scale_label}</text>"
        + "</g>"
    )

    north_arrow = (
        "<g transform='translate("
        + f"{margin_x + width_px + 120:.1f},{margin_y + 40:.1f}) rotate({north_rotation})' stroke='#0f172a' fill='none'>"
        + "<circle cx='0' cy='0' r='36' stroke-width='2.4' fill='rgba(14,116,144,0.08)' />"
        + "<polygon points='0,-26 11,10 -11,10' fill='#0f172a' />"
        + "<line x1='0' y1='10' x2='0' y2='28' stroke-width='3.4' />"
        + "<text x='0' y='48' font-size='14' font-family='Inter, sans-serif' font-weight='600' text-anchor='middle' fill='#0f172a'>N</text>"
        + "</g>"
    )

    svg = (
        f"<svg viewBox='0 0 {view_width:.1f} {view_height:.1f}' xmlns='http://www.w3.org/2000/svg' style='background:#f8fafc;border-radius:22px;box-shadow:0 30px 70px rgba(15,23,42,0.16)'>"
        "<defs>"
        "<marker id='arrow' markerWidth='8' markerHeight='8' refX='4' refY='4' orient='auto-start-reverse'>"
        "<path d='M0,0 L8,4 L0,8 z' fill='#94a3b8'/></marker>"
        "<style>.room:hover{cursor:pointer;opacity:0.96;} text{paint-order:stroke;stroke-width:0.2;stroke:#f8fafc;}</style>"
        f"{pattern_defs}"
        "</defs>"
        f"<rect x='{margin_x - 32:.1f}' y='{margin_y - 32:.1f}' width='{width_px + 64:.1f}' height='{length_px + 64:.1f}' fill='rgba(15,23,42,0.05)' stroke='#0f172a' stroke-width='1.6' stroke-dasharray='16 14' />"
        + "".join(grid_lines)
        + f"<path d='{path}' fill='rgba(148,163,184,0.12)' stroke='#0f172a' stroke-width='3' transform='translate({margin_x:.1f},{margin_y:.1f})' />"
        + "".join(room_layers)
        + dimension_lines
        + scale_bar
        + north_arrow
        + "</svg>"
    )
    metadata = {"scale_label": scale_label, "orientation": orientation.upper()}
    return svg, metadata


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


def _build_scale_label(width_m: float, length_m: float) -> str:
    _ = (width_m, length_m)
    return "Escala gráfica 1:100 (1 cm = 1 m)"


def _wrap_label(text: str, max_chars: int) -> list[str]:
    if max_chars <= 0:
        return [text]
    words = text.split()
    if not words:
        return [text]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if len(candidate) <= max_chars:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    while len(lines) > 3:
        tail = lines.pop()
        lines[-1] = f"{lines[-1]} {tail}".strip()
    wrapped = [line.strip() for line in lines if line.strip()]
    return wrapped or [text]


def _build_room_legend(rooms: list[dict[str, Any]]) -> list[dict[str, str]]:
    legend = []
    for room in rooms:
        legend.append(
            {
                "name": room["name"],
                "type": room.get("guide", {}).get("manual_step"),
                "area": f"{room['area']} m²",
                "dimensions": room.get("labels", {}).get("dimensions"),
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
        "boundary": form_data.get("boundary"),
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
