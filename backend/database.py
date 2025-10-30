"""SQLite database helpers for ConstruyeSeguro."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Iterable

DB_PATH = Path(__file__).resolve().parent.parent / "construyeseguro.db"


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    """Create all required tables if they do not exist."""
    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                form_data TEXT NOT NULL,
                results TEXT NOT NULL,
                viability REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS architects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                specialty TEXT NOT NULL,
                price_range TEXT NOT NULL,
                city TEXT NOT NULL,
                portfolio_url TEXT,
                rating REAL NOT NULL DEFAULT 4.5
            );

            CREATE TABLE IF NOT EXISTS suppliers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                address TEXT NOT NULL,
                city TEXT NOT NULL,
                contact TEXT NOT NULL,
                material_focus TEXT NOT NULL,
                latitude REAL,
                longitude REAL,
                rating REAL NOT NULL DEFAULT 4.0
            );

            CREATE TABLE IF NOT EXISTS financing_products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                provider TEXT NOT NULL,
                rate REAL NOT NULL,
                term_months INTEGER NOT NULL,
                product_type TEXT NOT NULL,
                requirements TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                youtube_id TEXT NOT NULL,
                level TEXT NOT NULL,
                description TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS testimonials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                author TEXT NOT NULL,
                location TEXT NOT NULL,
                quote TEXT NOT NULL
            );
            """
        )


def seed_data() -> None:
    """Populate lookup tables with example data when empty."""
    with get_connection() as connection:
        if not _has_rows(connection, "architects"):
            connection.executemany(
                """
                INSERT INTO architects (name, specialty, price_range, city, portfolio_url, rating)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        "Arq. Sofía Méndez",
                        "Vivienda sostenible",
                        "$15,000 - $25,000",
                        "Ciudad de México",
                        "https://portfolio.arqsofia.mx",
                        4.9,
                    ),
                    (
                        "Arq. Luis Herrera",
                        "Espacios comerciales y vivienda",
                        "$12,000 - $20,000",
                        "Guadalajara",
                        "https://luisherrera.studio",
                        4.7,
                    ),
                    (
                        "Arq. Daniela Flores",
                        "Diseño bioclimático",
                        "$18,000 - $30,000",
                        "Mérida",
                        "https://danielaflores.mx",
                        4.8,
                    ),
                ],
            )

        if not _has_rows(connection, "suppliers"):
            connection.executemany(
                """
                INSERT INTO suppliers (name, address, city, contact, material_focus, latitude, longitude, rating)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        "Materiales Rivera",
                        "Av. Central 123",
                        "Puebla",
                        "222-555-0192",
                        "Block y cemento",
                        19.0413,
                        -98.2062,
                        4.6,
                    ),
                    (
                        "EcoMaderas del Sur",
                        "Carretera 45 km 12",
                        "Oaxaca",
                        "951-332-1188",
                        "Madera tratada",
                        17.0594,
                        -96.7216,
                        4.4,
                    ),
                    (
                        "Hormigón Express",
                        "Calle 5 de Mayo 87",
                        "Monterrey",
                        "81-2456-7722",
                        "Concreto premezclado",
                        25.6866,
                        -100.3161,
                        4.2,
                    ),
                ],
            )

        if not _has_rows(connection, "financing_products"):
            connection.executemany(
                """
                INSERT INTO financing_products (name, provider, rate, term_months, product_type, requirements)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        "Crédito Construye Contigo",
                        "Finanzas Azteca",
                        12.5,
                        120,
                        "Hipotecario",
                        "Comprobación de ingresos, aval, historial crediticio positivo",
                    ),
                    (
                        "Microcrédito Materiales",
                        "Cooperativa Unión",
                        18.0,
                        36,
                        "Microfinanzas",
                        "Identificación oficial, comprobante de domicilio, plan de obra",
                    ),
                    (
                        "GreenHome Plus",
                        "Banco Sustentable",
                        9.8,
                        180,
                        "Hipotecario verde",
                        "Uso de materiales certificados y diseño bioclimático",
                    ),
                ],
            )

        if not _has_rows(connection, "videos"):
            connection.executemany(
                """
                INSERT INTO videos (title, category, youtube_id, level, description)
                VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (
                        "Cómo trazar cimientos seguros",
                        "cimientos",
                        "dQw4w9WgXcQ",
                        "nivel_1",
                        "Aprende a preparar el terreno y trazar cimientos resistentes.",
                    ),
                    (
                        "Muros de block paso a paso",
                        "estructura",
                        "V-_O7nl0Ii0",
                        "nivel_2",
                        "Técnicas para levantar muros rectos y alineados.",
                    ),
                    (
                        "Instalaciones eléctricas seguras",
                        "electricidad",
                        "iik25wqIuFo",
                        "nivel_3",
                        "Recomendaciones para cableado seguro en viviendas familiares.",
                    ),
                    (
                        "Acabados que duran",
                        "acabados",
                        "N3AkSS5hXMA",
                        "nivel_4",
                        "Consejos para aplicar acabados y pintura de larga duración.",
                    ),
                    (
                        "Ventilación natural efectiva",
                        "ventilacion",
                        "L_jWHffIx5E",
                        "general",
                        "Diseña aperturas y ductos para una ventilación pasiva.",
                    ),
                ],
            )

        if not _has_rows(connection, "testimonials"):
            connection.executemany(
                """
                INSERT INTO testimonials (author, location, quote)
                VALUES (?, ?, ?)
                """,
                [
                    (
                        "María y Antonio",
                        "Querétaro",
                        "Gracias a ConstruyeSeguro pudimos diseñar nuestra casa y terminarla en menos de 9 meses.",
                    ),
                    (
                        "Familia López",
                        "Chiapas",
                        "Las asesorías en línea nos ayudaron a evitar errores costosos en la estructura.",
                    ),
                    (
                        "Rocío",
                        "Jalisco",
                        "Los manuales paso a paso y los videos fueron clave para coordinar a nuestro equipo.",
                    ),
                ],
            )


def save_project(
    form_data: dict[str, Any],
    results: dict[str, Any],
    viability: float,
) -> int:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO projects (form_data, results, viability)
            VALUES (?, ?, ?)
            """,
            (json.dumps(form_data), json.dumps(results), viability),
        )
        return int(cursor.lastrowid)


def get_project(project_id: int) -> dict[str, Any] | None:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT id, form_data, results, viability, created_at FROM projects WHERE id = ?",
            (project_id,),
        ).fetchone()

    if row is None:
        return None

    return {
        "id": row["id"],
        "form_data": json.loads(row["form_data"]),
        "results": json.loads(row["results"]),
        "viability": row["viability"],
        "created_at": row["created_at"],
    }


def fetch_rows(query: str, params: Iterable[Any] | None = None) -> list[dict[str, Any]]:
    with get_connection() as connection:
        cursor = connection.execute(query, tuple(params or []))
        return [dict(row) for row in cursor.fetchall()]


def _has_rows(connection: sqlite3.Connection, table: str) -> bool:
    cursor = connection.execute(f"SELECT 1 FROM {table} LIMIT 1")
    return cursor.fetchone() is not None
