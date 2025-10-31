"""REST API routes for ConstruyeSeguro 2.0."""
from __future__ import annotations

import secrets
from functools import wraps
from http import HTTPStatus
from pathlib import Path

from flask import Blueprint, Response, current_app, g, jsonify, request, send_file
from werkzeug.security import check_password_hash, generate_password_hash

from . import database
from .services import financing, manual_builder, plan_generator, youtube_service
from .validation import validate_project_payload

api_bp = Blueprint("api", __name__)


# ---------------------------------------------------------------------------
# Authentication helpers
# ---------------------------------------------------------------------------
def _extract_token() -> str:
    header = request.headers.get("Authorization", "")
    if header.lower().startswith("bearer "):
        return header.split(" ", 1)[1]
    return request.cookies.get("auth_token", "")


def require_auth(handler):
    @wraps(handler)
    def wrapper(*args, **kwargs):
        token = _extract_token()
        user = database.get_user_by_token(token)
        if not user:
            return jsonify({"error": "Autenticación requerida"}), HTTPStatus.UNAUTHORIZED
        g.current_user = user
        g.auth_token = token
        return handler(*args, **kwargs)

    return wrapper


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------
@api_bp.post("/auth/register")
def register() -> tuple[Response, int]:
    payload = request.get_json(force=True, silent=True) or {}
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""
    full_name = (payload.get("full_name") or "").strip() or None

    if not email or "@" not in email:
        return jsonify({"error": "Correo electrónico inválido"}), HTTPStatus.BAD_REQUEST
    if len(password) < 8:
        return jsonify({"error": "La contraseña debe tener al menos 8 caracteres"}), HTTPStatus.BAD_REQUEST
    if database.get_user_by_email(email):
        return jsonify({"error": "Ya existe una cuenta con ese correo"}), HTTPStatus.CONFLICT

    password_hash = generate_password_hash(password)
    user_id = database.create_user(email, password_hash, full_name)
    token = secrets.token_urlsafe(32)
    database.create_session(token, user_id)

    return (
        jsonify(
            {
                "token": token,
                "user": {"id": user_id, "email": email, "full_name": full_name},
            }
        ),
        HTTPStatus.CREATED,
    )


@api_bp.post("/auth/login")
def login() -> tuple[Response, int]:
    payload = request.get_json(force=True, silent=True) or {}
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""

    user = database.get_user_by_email(email)
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Credenciales inválidas"}), HTTPStatus.UNAUTHORIZED

    token = secrets.token_urlsafe(32)
    database.create_session(token, int(user["id"]))

    return (
        jsonify(
            {
                "token": token,
                "user": {
                    "id": int(user["id"]),
                    "email": user["email"],
                    "full_name": user.get("full_name"),
                },
            }
        ),
        HTTPStatus.OK,
    )


@api_bp.post("/auth/logout")
@require_auth
def logout() -> tuple[Response, int]:
    database.revoke_session(g.auth_token)
    return jsonify({"status": "Sesión cerrada"}), HTTPStatus.OK


# ---------------------------------------------------------------------------
# Project and plan routes
# ---------------------------------------------------------------------------
@api_bp.get("/projects")
@require_auth
def list_projects() -> Response:
    user_id = int(g.current_user["id"])
    projects = database.list_user_projects(user_id)
    watched_ids = database.get_watched_video_ids(user_id)
    total_videos = max(database.total_videos(), 1)
    video_progress = round(len(watched_ids) / total_videos, 2)

    for project in projects:
        project["video_progress"] = video_progress
        project["videos_watched"] = len(watched_ids)
        project["total_videos"] = total_videos
    return jsonify({"projects": projects})


@api_bp.post("/projects")
@require_auth
def create_project() -> tuple[Response, int]:
    payload = request.get_json(force=True, silent=True) or {}
    project_data = validate_project_payload(payload)
    generated = plan_generator.generate_project_package(project_data)

    project_title = payload.get("title") or f"Proyecto {project_data['ciudad']}"
    user_id = int(g.current_user["id"])
    project_id = database.create_user_project(
        user_id=user_id,
        title=project_title,
        form_data=project_data,
        plan_data=generated,
        viability=generated["viability"]["score"],
    )

    storage_dir: Path = current_app.config["PROJECT_STORAGE"]
    storage_dir.mkdir(parents=True, exist_ok=True)
    manual_path = storage_dir / f"manual_{user_id}_{project_id}.pdf"
    manual_builder.generate_manual_pdf(project_id, generated, manual_path)
    database.set_project_manual_path(project_id, str(manual_path))

    generated["project_id"] = project_id
    generated["manual_url"] = f"/api/projects/{project_id}/manual/pdf"

    return jsonify(generated), HTTPStatus.CREATED


@api_bp.get("/projects/<int:project_id>")
@require_auth
def get_project(project_id: int) -> tuple[Response, int]:
    user_id = int(g.current_user["id"])
    project = database.get_user_project(project_id, user_id)
    if project is None:
        return jsonify({"error": "Proyecto no encontrado"}), HTTPStatus.NOT_FOUND
    watched_ids = database.get_watched_video_ids(user_id)
    total_videos = max(database.total_videos(), 1)
    project["video_progress"] = round(len(watched_ids) / total_videos, 2)
    project["videos_watched"] = len(watched_ids)
    project["total_videos"] = total_videos
    return jsonify(project), HTTPStatus.OK


@api_bp.get("/projects/<int:project_id>/manual/pdf")
@require_auth
def download_manual(project_id: int):
    user_id = int(g.current_user["id"])
    project = database.get_user_project(project_id, user_id)
    if project is None:
        return jsonify({"error": "Proyecto no encontrado"}), HTTPStatus.NOT_FOUND

    manual_path = Path(project.get("manual_path") or "")
    storage_dir: Path = current_app.config["PROJECT_STORAGE"]
    if not manual_path.exists():
        manual_path = storage_dir / f"manual_{user_id}_{project_id}.pdf"
        manual_builder.generate_manual_pdf(project_id, project["plan_data"], manual_path)
        database.set_project_manual_path(project_id, str(manual_path))

    database.record_manual_download(user_id, project_id)
    return send_file(manual_path, download_name=f"manual_construyeseguro_{project_id}.pdf")


@api_bp.post("/plan")
@require_auth
def preview_plan() -> Response:
    payload = request.get_json(force=True, silent=True) or {}
    project_data = validate_project_payload(payload)
    generated = plan_generator.generate_project_package(project_data)
    return jsonify(generated)


# ---------------------------------------------------------------------------
# Video library
# ---------------------------------------------------------------------------
VIDEO_LEVEL_ORDER = {"principiante": 0, "intermedio": 1, "avanzado": 2}


@api_bp.get("/videos")
@require_auth
def list_videos() -> Response:
    level = request.args.get("level")
    category = request.args.get("category")
    search = request.args.get("search")
    rows = youtube_service.list_videos(category=category, search=search)

    if level:
        rows = [row for row in rows if row["level"].lower() == level.lower()]

    rows.sort(key=lambda item: (VIDEO_LEVEL_ORDER.get(item["level"], 99), item["title"]))

    watched_ids = database.get_watched_video_ids(int(g.current_user["id"]))
    for row in rows:
        row["watched"] = row.get("id") in watched_ids
    return jsonify({"videos": rows})


@api_bp.post("/videos/<int:video_id>/watch")
@require_auth
def track_video(video_id: int) -> tuple[Response, int]:
    database.record_video_watch(int(g.current_user["id"]), video_id)
    watched = len(database.get_watched_video_ids(int(g.current_user["id"])))
    total = max(database.total_videos(), 1)
    progress = round(watched / total, 2)
    return jsonify({"progress": progress, "watched": watched, "total": total}), HTTPStatus.CREATED


# ---------------------------------------------------------------------------
# Manual overview and marketplace utilities
# ---------------------------------------------------------------------------
@api_bp.get("/manual/steps")
@require_auth
def manual_steps() -> Response:
    level = request.args.get("level")
    steps = manual_builder.build_manual_steps(level_filter=level)
    return jsonify({"steps": steps})


@api_bp.get("/marketplace/architects")
def list_architects() -> Response:
    city = request.args.get("city")
    specialty = request.args.get("specialty")
    architects = database.fetch_rows(
        """
        SELECT name, specialty, price_range, city, portfolio_url, rating
        FROM architects
        WHERE (? IS NULL OR city = ?)
        AND (? IS NULL OR specialty = ?)
        ORDER BY rating DESC
        """,
        (city, city, specialty, specialty),
    )
    return jsonify({"architects": architects})


@api_bp.get("/marketplace/suppliers")
def list_suppliers() -> Response:
    city = request.args.get("city")
    material = request.args.get("material")
    suppliers = database.fetch_rows(
        """
        SELECT name, address, city, contact, material_focus, latitude, longitude, rating
        FROM suppliers
        WHERE (? IS NULL OR city = ?)
        AND (? IS NULL OR material_focus = ?)
        ORDER BY rating DESC
        """,
        (city, city, material, material),
    )
    return jsonify({"suppliers": suppliers})


@api_bp.get("/marketplace/alerts")
def safety_alerts() -> Response:
    alerts = [
        "Utiliza señalización perimetral y cinta de peligro durante toda la obra.",
        "Verifica que el contratista cuente con equipo de seguridad personal (EPP).",
        "Coordina con vecinos horarios de obra para minimizar molestias.",
    ]
    return jsonify({"alerts": alerts})


@api_bp.get("/testimonials")
def testimonials() -> Response:
    rows = database.fetch_rows("SELECT author, location, quote FROM testimonials")
    return jsonify({"testimonials": rows})


@api_bp.get("/financing/products")
def financing_products() -> Response:
    product_type = request.args.get("type")
    products = financing.get_financing_products(product_type=product_type)
    return jsonify({"products": products})


@api_bp.get("/financing/simulate")
def simulate_financing() -> Response:
    amount = float(request.args.get("amount", 0))
    months = int(request.args.get("months", 0))
    rate = float(request.args.get("rate", 0))
    simulation = financing.simulate_payment_plan(amount=amount, months=months, rate=rate)
    return jsonify(simulation)


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------
@api_bp.errorhandler(ValueError)
def handle_validation_error(exc: ValueError) -> tuple[Response, int]:
    return jsonify({"error": str(exc)}), HTTPStatus.BAD_REQUEST


@api_bp.errorhandler(Exception)
def handle_generic_error(exc: Exception) -> tuple[Response, int]:
    current_app.logger.exception("Unhandled error: %s", exc)
    return jsonify({"error": "Ocurrió un error inesperado"}), HTTPStatus.INTERNAL_SERVER_ERROR
