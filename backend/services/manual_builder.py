"""Manual generation utilities, including PDF export."""
from __future__ import annotations

from pathlib import Path
from textwrap import wrap
from typing import Any

from .youtube_service import get_manual_videos

LINE_WIDTH = 90


def build_manual_steps(level_filter: str | None = None) -> list[dict[str, Any]]:
    """Return the canonical manual steps, optionally filtered by level."""
    levels = [
        {
            "level": "principiante",
            "title": "Principiante: Preparación y cimientos",
            "summary": "Preparación del terreno, trazos, compactación y cimentación segura.",
        },
        {
            "level": "intermedio",
            "title": "Intermedio: Muros e instalaciones",
            "summary": "Levantamiento de muros, instalaciones hidráulicas y eléctricas básicas.",
        },
        {
            "level": "avanzado",
            "title": "Avanzado: Acabados y supervisión",
            "summary": "Acabados, impermeabilización, revisión de seguridad y entrega.",
        },
    ]
    if level_filter:
        levels = [level for level in levels if level["level"] == level_filter]
    for level in levels:
        level["videos"] = get_manual_videos(level["level"])
    return levels


def generate_manual_pdf(
    project_id: int,
    project_summary: dict[str, Any],
    destination: Path,
) -> None:
    """Generate a lightweight PDF manual for offline consultation."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    contents = _compose_pdf_content(project_id, project_summary)
    destination.write_bytes(contents)


def _compose_pdf_content(project_id: int, project_summary: dict[str, Any]) -> bytes:
    lines = ["ConstruyeSeguro - Manual Constructivo", f"Proyecto #{project_id}", ""]

    overview = project_summary.get("overview", {})
    terrain = overview.get("terrain", {})
    lines.extend(
        [
            "Resumen del Proyecto:",
            f"  Terreno: {terrain.get('width', 0)}m x {terrain.get('length', 0)}m",
            f"  Niveles: {overview.get('levels', 1)}",
            f"  Material principal: {overview.get('material', '').title()}",
            "",
        ]
    )

    viability = project_summary.get("viability", {})
    lines.append(f"Viabilidad estimada: {viability.get('score', 0) * 100:.0f}% - {viability.get('message', '')}")
    lines.append("")

    lines.append("Pasos principales:")
    for step in project_summary.get("manual", {}).get("steps", []):
        lines.append(f"  Paso {step['step']}: {step['description']}")
        video = step.get("video") or {}
        if video:
            video_url = video.get("url") or f"https://www.youtube.com/watch?v={video.get('youtube_id')}"
            lines.append(f"    Video: {video_url}")
    lines.append("")

    lines.append("Materiales principales:")
    for item in project_summary.get("materials", {}).get("items", []):
        lines.append(
            f"  - {item['name']} - {item['quantity']} {item['unit']} (Costo unitario: ${item['unit_cost']})"
        )

    return _build_pdf_from_lines(lines)


def _build_pdf_from_lines(lines: list[str]) -> bytes:
    wrapped_lines: list[str] = []
    for line in lines:
        wrapped_lines.extend(wrap(line, width=LINE_WIDTH) or [""])

    y_position = 780
    leading = 14
    content_stream_lines = ["BT", "/F1 18 Tf", "72 800 Td", f"(ConstruyeSeguro) Tj", "T*", "T*", "/F1 12 Tf"]
    for wrapped in wrapped_lines:
        safe_text = _escape_pdf_text(wrapped)
        content_stream_lines.append(f"({safe_text}) Tj")
        content_stream_lines.append(f"0 -{leading} Td")
        y_position -= leading
        if y_position <= 80:
            break
    content_stream_lines.append("ET")
    content_stream = "\n".join(content_stream_lines).encode("utf-8")

    pdf_header = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
    objects: list[bytes] = []
    offsets: list[int] = []
    current_offset = len(pdf_header)

    def add_object(payload: bytes) -> None:
        nonlocal current_offset
        offsets.append(current_offset)
        if not payload.endswith(b"\n"):
            payload += b"\n"
        objects.append(payload)
        current_offset += len(payload)

    add_object(b"1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj")
    add_object(b"2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj")
    add_object(
        (
            "3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            "/Contents 4 0 R /Resources<< /Font<< /F1 5 0 R >> >> >>endobj"
        ).encode("utf-8")
    )
    add_object(
        f"4 0 obj<< /Length {len(content_stream)} >>stream\n".encode("utf-8")
        + content_stream
        + b"\nendstream\nendobj"
    )
    add_object(b"5 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj")

    xref_position = current_offset
    xref_table = ["xref", "0 6", "0000000000 65535 f "]
    for offset in offsets:
        xref_table.append(f"{offset:010d} 00000 n ")
    trailer = [
        "trailer<< /Size 6 /Root 1 0 R >>",
        f"startxref\n{xref_position}",
        "%%EOF",
    ]

    pdf_parts = [pdf_header] + objects + ["\n".join(xref_table).encode("utf-8"), "\n".join(trailer).encode("utf-8")]
    return b"".join(pdf_parts)


def _escape_pdf_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
