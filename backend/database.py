"""SQLite database helpers for ConstruyeSeguro."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Iterable

from .data.video_catalog import VIDEO_CATALOG

DB_PATH = Path(__file__).resolve().parent.parent / "construyeseguro.db"


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _ensure_column(connection: sqlite3.Connection, table: str, column: str, alter_sql: str) -> None:
    """Add a column to an existing table when seeding legacy databases."""
    columns = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
    if column not in columns:
        connection.execute(alter_sql)


def init_db() -> None:
    """Create all required tables if they do not exist."""
    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                full_name TEXT,
                city TEXT,
                project_type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS user_projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                form_data TEXT NOT NULL,
                plan_data TEXT NOT NULL,
                viability REAL NOT NULL,
                manual_path TEXT,
                status TEXT NOT NULL DEFAULT 'En preparación',
                progress REAL NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS video_watch_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                video_id INTEGER NOT NULL,
                watched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (user_id, video_id),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS manual_downloads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                project_id INTEGER NOT NULL,
                downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (project_id) REFERENCES user_projects(id) ON DELETE CASCADE
            );

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
                stage TEXT,
                description TEXT NOT NULL,
                manual_step TEXT,
                tags TEXT
            );

            CREATE TABLE IF NOT EXISTS providers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                provider_type TEXT NOT NULL,
                specialty TEXT,
                city TEXT NOT NULL,
                locality TEXT,
                price_min REAL,
                price_max REAL,
                rating REAL DEFAULT 4.6,
                description TEXT,
                contact TEXT,
                portfolio_url TEXT,
                experience_years INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS project_hires (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                project_id INTEGER NOT NULL,
                provider_id INTEGER NOT NULL,
                message TEXT,
                status TEXT NOT NULL DEFAULT 'pendiente',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (project_id) REFERENCES user_projects(id) ON DELETE CASCADE,
                FOREIGN KEY (provider_id) REFERENCES providers(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS testimonials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                author TEXT NOT NULL,
                location TEXT NOT NULL,
                quote TEXT NOT NULL
            );
            """
        )

        _ensure_column(connection, "users", "city", "ALTER TABLE users ADD COLUMN city TEXT")
        _ensure_column(
            connection,
            "users",
            "project_type",
            "ALTER TABLE users ADD COLUMN project_type TEXT",
        )
        _ensure_column(connection, "videos", "stage", "ALTER TABLE videos ADD COLUMN stage TEXT")
        _ensure_column(connection, "videos", "tags", "ALTER TABLE videos ADD COLUMN tags TEXT")


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

        if not _has_rows(connection, "providers"):
            connection.executemany(
                """
                INSERT INTO providers (
                    name, provider_type, specialty, city, locality, price_min, price_max, rating, description, contact, portfolio_url, experience_years
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        "Arq. Sofía Méndez",
                        "arquitectura",
                        "Vivienda sostenible",
                        "Ciudad de México",
                        "Iztapalapa",
                        15000,
                        25000,
                        4.9,
                        "Diseños bioclimáticos con enfoque en autoconstrucción asistida.",
                        "contacto@arqsofia.mx",
                        "https://portfolio.arqsofia.mx",
                        12,
                    ),
                    (
                        "Ing. Luis Herrera",
                        "asesoría",
                        "Supervisión estructural",
                        "Guadalajara",
                        "Tonalá",
                        8000,
                        15000,
                        4.7,
                        "Acompañamiento técnico para cimentación y estructura ligera.",
                        "hola@lhuconsultores.com",
                        "https://lhuconsultores.com",
                        15,
                    ),
                    (
                        "Ferretería El Puente",
                        "materiales",
                        "Materiales y herramientas",
                        "Puebla",
                        "Cholula",
                        500,
                        8000,
                        4.5,
                        "Entrega a obra y paquetes especiales para autoconstructores.",
                        "ventas@ferreteriaelpuente.mx",
                        "https://ferreteriaelpuente.mx",
                        20,
                    ),
                    (
                        "Constructora Norte",
                        "arquitectura",
                        "Planos ejecutivos y permisos",
                        "Monterrey",
                        "Centro",
                        18000,
                        32000,
                        4.8,
                        "Equipo multidisciplinario especializado en vivienda progresiva.",
                        "contacto@constructoranorte.mx",
                        "https://constructoranorte.mx",
                        18,
                    ),
                    (
                        "Materiales Rivera",
                        "materiales",
                        "Concreto y block",
                        "Querétaro",
                        "San Pedro",
                        400,
                        6000,
                        4.6,
                        "Proveedores certificados con logística para zonas rurales.",
                        "ventas@materialesrivera.com",
                        "https://materialesrivera.com",
                        22,
                    ),
                ],
            )

        _seed_video_catalog(connection)

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


def create_user(
    email: str,
    password_hash: str,
    full_name: str | None = None,
    *,
    city: str | None = None,
    project_type: str | None = None,
) -> int:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO users (email, password_hash, full_name, city, project_type)
            VALUES (?, ?, ?, ?, ?)
            """,
            (email.lower(), password_hash, full_name, city, project_type),
        )
        return int(cursor.lastrowid)


def get_user_by_email(email: str) -> dict[str, Any] | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT id, email, password_hash, full_name, city, project_type, created_at
            FROM users
            WHERE email = ?
            """,
            (email.lower(),),
        ).fetchone()
    return dict(row) if row else None


def get_user_by_id(user_id: int) -> dict[str, Any] | None:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT id, email, full_name, city, project_type, created_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    return dict(row) if row else None


def create_session(token: str, user_id: int) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT OR REPLACE INTO sessions (token, user_id)
            VALUES (?, ?)
            """,
            (token, user_id),
        )


def get_user_by_token(token: str) -> dict[str, Any] | None:
    if not token:
        return None
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT users.id, users.email, users.full_name, users.city, users.project_type
            FROM sessions
            JOIN users ON users.id = sessions.user_id
            WHERE sessions.token = ?
            """,
            (token,),
        ).fetchone()
    return dict(row) if row else None


def revoke_session(token: str) -> None:
    with get_connection() as connection:
        connection.execute("DELETE FROM sessions WHERE token = ?", (token,))


def create_user_project(
    user_id: int,
    title: str,
    form_data: dict[str, Any],
    plan_data: dict[str, Any],
    viability: float,
    manual_path: str | None = None,
    status: str = "En preparación",
) -> int:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO user_projects (user_id, title, form_data, plan_data, viability, manual_path, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                title,
                json.dumps(form_data),
                json.dumps(plan_data),
                viability,
                manual_path,
                status,
            ),
        )
        return int(cursor.lastrowid)


def update_project_progress(project_id: int, *, progress: float | None = None, status: str | None = None) -> None:
    assignments: list[str] = []
    params: list[Any] = []
    if progress is not None:
        assignments.append("progress = ?")
        params.append(progress)
    if status is not None:
        assignments.append("status = ?")
        params.append(status)
    if not assignments:
        return
    params.append(project_id)
    with get_connection() as connection:
        connection.execute(
            f"UPDATE user_projects SET {', '.join(assignments)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            tuple(params),
        )


def set_project_manual_path(project_id: int, manual_path: str) -> None:
    with get_connection() as connection:
        connection.execute(
            "UPDATE user_projects SET manual_path = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (manual_path, project_id),
        )


def list_user_projects(user_id: int) -> list[dict[str, Any]]:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            SELECT id, title, form_data, plan_data, viability, manual_path, status, progress, created_at, updated_at
            FROM user_projects
            WHERE user_id = ?
            ORDER BY created_at DESC
            """,
            (user_id,),
        )
        projects: list[dict[str, Any]] = []
        for row in cursor.fetchall():
            project = dict(row)
            project["form_data"] = json.loads(project["form_data"])
            project["plan_data"] = json.loads(project["plan_data"])
            projects.append(project)
        return projects


def get_user_project(project_id: int, user_id: int) -> dict[str, Any] | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT id, title, form_data, plan_data, viability, manual_path, status, progress, created_at, updated_at
            FROM user_projects
            WHERE id = ? AND user_id = ?
            """,
            (project_id, user_id),
        ).fetchone()
    if row is None:
        return None
    project = dict(row)
    project["form_data"] = json.loads(project["form_data"])
    project["plan_data"] = json.loads(project["plan_data"])
    return project


def record_video_watch(user_id: int, video_id: int) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT OR IGNORE INTO video_watch_history (user_id, video_id)
            VALUES (?, ?)
            """,
            (user_id, video_id),
        )


def get_watched_video_ids(user_id: int) -> set[int]:
    with get_connection() as connection:
        cursor = connection.execute(
            "SELECT video_id FROM video_watch_history WHERE user_id = ?",
            (user_id,),
        )
        return {row["video_id"] for row in cursor.fetchall()}


def total_videos() -> int:
    with get_connection() as connection:
        (count,) = connection.execute("SELECT COUNT(*) FROM videos").fetchone()
    return int(count)


def list_videos(
    *,
    level: str | None = None,
    category: str | None = None,
    stage: str | None = None,
    search: str | None = None,
) -> list[dict[str, Any]]:
    query = "SELECT id, title, category, youtube_id, level, stage, description, manual_step, tags FROM videos"
    clauses: list[str] = []
    params: list[Any] = []
    if level:
        clauses.append("LOWER(level) = LOWER(?)")
        params.append(level)
    if category:
        clauses.append("LOWER(category) = LOWER(?)")
        params.append(category)
    if stage:
        clauses.append("LOWER(stage) = LOWER(?)")
        params.append(stage)
    if search:
        clauses.append("LOWER(title) LIKE ?")
        params.append(f"%{search.lower()}%")
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY CASE LOWER(level) WHEN 'principiante' THEN 0 WHEN 'intermedio' THEN 1 WHEN 'avanzado' THEN 2 ELSE 3 END, stage, title"
    return fetch_rows(query, params)


def record_manual_download(user_id: int, project_id: int) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO manual_downloads (user_id, project_id)
            VALUES (?, ?)
            """,
            (user_id, project_id),
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


def list_providers(
    *,
    city: str | None = None,
    provider_type: str | None = None,
    price_min: float | None = None,
    price_max: float | None = None,
) -> list[dict[str, Any]]:
    query = (
        "SELECT id, name, provider_type, specialty, city, locality, price_min, price_max, rating, description, contact, portfolio_url, experience_years "
        "FROM providers"
    )
    clauses: list[str] = []
    params: list[Any] = []
    if city:
        clauses.append("LOWER(city) = LOWER(?)")
        params.append(city)
    if provider_type:
        clauses.append("LOWER(provider_type) = LOWER(?)")
        params.append(provider_type)
    if price_min is not None:
        clauses.append("(price_max IS NULL OR price_max >= ?)")
        params.append(price_min)
    if price_max is not None:
        clauses.append("(price_min IS NULL OR price_min <= ?)")
        params.append(price_max)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY rating DESC, price_min"
    return fetch_rows(query, params)


def get_provider(provider_id: int) -> dict[str, Any] | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT id, name, provider_type, specialty, city, locality, price_min, price_max, rating, description, contact, portfolio_url, experience_years
            FROM providers
            WHERE id = ?
            """,
            (provider_id,),
        ).fetchone()
    return dict(row) if row else None


def create_hire_request(
    *,
    user_id: int,
    project_id: int,
    provider_id: int,
    message: str | None = None,
) -> int:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO project_hires (user_id, project_id, provider_id, message)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, project_id, provider_id, message),
        )
        return int(cursor.lastrowid)


def list_hire_requests(user_id: int) -> list[dict[str, Any]]:
    return fetch_rows(
        """
        SELECT project_hires.id, project_hires.project_id, project_hires.status, project_hires.created_at,
               providers.name AS provider_name, providers.provider_type, providers.city, providers.contact
        FROM project_hires
        JOIN providers ON providers.id = project_hires.provider_id
        WHERE project_hires.user_id = ?
        ORDER BY project_hires.created_at DESC
        """,
        (user_id,),
    )


def fetch_rows(query: str, params: Iterable[Any] | None = None) -> list[dict[str, Any]]:
    with get_connection() as connection:
        cursor = connection.execute(query, tuple(params or []))
        return [dict(row) for row in cursor.fetchall()]


def _has_rows(connection: sqlite3.Connection, table: str) -> bool:
    cursor = connection.execute(f"SELECT 1 FROM {table} LIMIT 1")
    return cursor.fetchone() is not None


def _seed_video_catalog(connection: sqlite3.Connection) -> None:
    """Ensure the bundled video catalog is available in the database."""

    cursor = connection.execute("SELECT youtube_id FROM videos")
    existing_ids = {row["youtube_id"] for row in cursor.fetchall()}
    catalog_ids = {item["youtube_id"] for item in VIDEO_CATALOG}

    if existing_ids == catalog_ids and len(existing_ids) == len(VIDEO_CATALOG):
        return

    connection.execute("DELETE FROM video_watch_history")
    connection.execute("DELETE FROM videos")
    connection.executemany(
        """
        INSERT INTO videos (title, category, youtube_id, level, stage, description, manual_step, tags)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                video["title"],
                video["category"],
                video["youtube_id"],
                video["level"],
                video.get("stage"),
                video.get("description"),
                video.get("manual_step"),
                video.get("tags", ""),
            )
            for video in VIDEO_CATALOG
        ],
    )
