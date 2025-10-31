"""Seed script to populate the ConstruyeSeguro video library."""
from __future__ import annotations

from backend import database

VIDEO_DATA = [
    {
        "title": "¿Qué es la autoproducción de vivienda?",
        "category": "cimientos",
        "youtube_id": "q3Xum8KQp4k",
        "level": "principiante",
        "description": "Introducción a la autoconstrucción responsable y organización del terreno.",
        "manual_step": "preparacion_terreno",
    },
    {
        "title": "Preparar el terreno y cimentar paso a paso",
        "category": "cimientos",
        "youtube_id": "ml9Z3l0l6eU",
        "level": "principiante",
        "description": "Limpieza, nivelación y armado de cimientos seguros para viviendas familiares.",
        "manual_step": "preparacion_terreno",
    },
    {
        "title": "5 errores comunes en la autoconstrucción",
        "category": "estructura",
        "youtube_id": "N5pQuG2X3SE",
        "level": "intermedio",
        "description": "Errores frecuentes al levantar muros y cómo evitarlos con buenas prácticas.",
        "manual_step": "levantamiento_muros",
    },
    {
        "title": "Instalaciones hidráulicas y eléctricas seguras",
        "category": "instalaciones",
        "youtube_id": "V7gJQsxrBn0",
        "level": "intermedio",
        "description": "Planeación de ductos, tuberías y tableros para garantizar seguridad y mantenimiento.",
        "manual_step": "instalaciones_seguras",
    },
    {
        "title": "Acabados profesionales en muros y pisos",
        "category": "acabados",
        "youtube_id": "j9QwJbiZ5fE",
        "level": "avanzado",
        "description": "Técnicas de nivelado, sellado e impermeabilización para entregar tu vivienda.",
        "manual_step": "acabados_finales",
    },
    {
        "title": "Ventilación e iluminación natural en tu hogar",
        "category": "ventilacion",
        "youtube_id": "p70zRz3WcKU",
        "level": "principiante",
        "description": "Cómo orientar espacios y abrir vanos para aprovechar el asoleamiento.",
        "manual_step": "ventilacion_iluminacion",
    },
]


def main() -> None:
    database.init_db()
    with database.get_connection() as connection:
        for video in VIDEO_DATA:
            connection.execute(
                """
                INSERT OR IGNORE INTO videos (title, category, youtube_id, level, description, manual_step)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    video["title"],
                    video["category"],
                    video["youtube_id"],
                    video["level"],
                    video["description"],
                    video["manual_step"],
                ),
            )
    print("Catálogo de videos actualizado correctamente.")


if __name__ == "__main__":
    main()
