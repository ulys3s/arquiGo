"""REST API routes for ConstruyeSeguro 2.0."""
from __future__ import annotations

import secrets
from functools import wraps
from http import HTTPStatus
from pathlib import Path
from typing import Any

from flask import Blueprint, Response, current_app, g, jsonify, make_response, request, send_file
from werkzeug.security import check_password_hash, generate_password_hash

from . import database
from .models import Provider, User, Video
from .services import financing, manual_builder, plan_generator, youtube_service
from .validation import validate_project_payload

api_bp = Blueprint("api", __name__)

SESSION_COOKIE_NAME = "cs_session"
SESSION_COOKIE_MAX_AGE = 60 * 60 * 24 * 30  # 30 days


# ---------------------------------------------------------------------------
# Authentication helpers
# ---------------------------------------------------------------------------
def _extract_token() -> str:
    header = request.headers.get("Authorization", "")
    if header.lower().startswith("bearer "):
        return header.split(" ", 1)[1]
    return request.cookies.get(SESSION_COOKIE_NAME, "")


def _set_session_cookie(response: Response, token: str) -> None:
    secure_cookie = current_app.config.get("SESSION_COOKIE_SECURE", False)
    response.set_cookie(
        SESSION_COOKIE_NAME,
        token,
        max_age=SESSION_COOKIE_MAX_AGE,
        httponly=True,
        secure=secure_cookie,
        samesite="Lax",
        path="/",
    )


def _clear_session_cookie(response: Response) -> None:
    response.set_cookie(
        SESSION_COOKIE_NAME,
        "",
        expires=0,
        max_age=0,
        httponly=True,
        secure=current_app.config.get("SESSION_COOKIE_SECURE", False),
        samesite="Lax",
        path="/",
    )


def require_auth(handler):
    @wraps(handler)
    def wrapper(*args, **kwargs):
        token = _extract_token()
        user_row = database.get_user_by_token(token)
        user: User | None = User.from_row(user_row) if user_row else None
        if not user:
            return (
                jsonify({"success": False, "error": "Autenticación requerida"}),
                HTTPStatus.UNAUTHORIZED,
            )
        g.current_user = user
        g.auth_token = token
        return handler(*args, **kwargs)

    return wrapper


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------
@api_bp.post("/register")
@api_bp.post("/auth/register")
def register() -> Response:
    payload = request.get_json(force=True, silent=True) or {}
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""
    full_name = (payload.get("full_name") or "").strip() or None
    city = (payload.get("city") or "").strip() or None
    project_type = (payload.get("project_type") or "").strip() or None

    if not email or "@" not in email:
        return (
            jsonify({"success": False, "error": "Correo electrónico inválido"}),
            HTTPStatus.BAD_REQUEST,
        )
    if len(password) < 8:
        return (
            jsonify(
                {
                    "success": False,
                    "error": "La contraseña debe tener al menos 8 caracteres",
                }
            ),
            HTTPStatus.BAD_REQUEST,
        )
    if database.get_user_by_email(email):
        return (
            jsonify({"success": False, "error": "Ya existe una cuenta con ese correo"}),
            HTTPStatus.CONFLICT,
        )

    password_hash = generate_password_hash(password)
    user_id = database.create_user(
        email,
        password_hash,
        full_name,
        city=city,
        project_type=project_type,
    )
    token = secrets.token_urlsafe(32)
    database.create_session(token, user_id)

    response = make_response(
        jsonify(
            {
                "success": True,
                "message": "Cuenta creada correctamente",
                "token": token,
                "user": {
                    "id": user_id,
                    "email": email,
                    "full_name": full_name,
                    "city": city,
                    "project_type": project_type,
                },
            }
        ),
        HTTPStatus.CREATED,
    )
    _set_session_cookie(response, token)
    return response


@api_bp.post("/login")
@api_bp.post("/auth/login")
def login() -> Response:
    payload = request.get_json(force=True, silent=True) or {}
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""

    user = database.get_user_by_email(email)
    if not user or not check_password_hash(user["password_hash"], password):
        return (
            jsonify({"success": False, "error": "Credenciales inválidas"}),
            HTTPStatus.UNAUTHORIZED,
        )

    token = secrets.token_urlsafe(32)
    database.create_session(token, int(user["id"]))

    response = make_response(
        jsonify(
            {
                "success": True,
                "message": "Sesión iniciada",
                "token": token,
                "user": {
                    "id": int(user["id"]),
                    "email": user["email"],
                    "full_name": user.get("full_name"),
                    "city": user.get("city"),
                    "project_type": user.get("project_type"),
                },
            }
        ),
        HTTPStatus.OK,
    )
    _set_session_cookie(response, token)
    return response


@api_bp.post("/logout")
@api_bp.post("/auth/logout")
@require_auth
def logout() -> Response:
    database.revoke_session(g.auth_token)
    response = make_response(jsonify({"success": True, "message": "Sesión cerrada"}), HTTPStatus.OK)
    _clear_session_cookie(response)
    return response


# ---------------------------------------------------------------------------
# Project and plan routes
# ---------------------------------------------------------------------------
@api_bp.get("/projects")
@require_auth
def list_projects() -> Response:
    user_id = g.current_user.id
    projects = database.list_user_projects(user_id)
    watched_ids = database.get_watched_video_ids(user_id)
    total_videos = max(database.total_videos(), 1)
    video_progress = round(len(watched_ids) / total_videos, 2)

    for project in projects:
        manual = (project.get("plan_data") or {}).get("manual") or {}
        if "recommended_videos" not in manual:
            manual["recommended_videos"] = youtube_service.recommended_videos_for_project(
                project.get("form_data", {})
            )
            project.setdefault("plan_data", {})["manual"] = manual
        project["video_progress"] = video_progress
        project["videos_watched"] = len(watched_ids)
        project["total_videos"] = total_videos
    return jsonify({"success": True, "projects": projects})


@api_bp.get("/dashboard")
@require_auth
def dashboard() -> Response:
    user_id = g.current_user.id
    projects = database.list_user_projects(user_id)
    watched_ids = database.get_watched_video_ids(user_id)
    total_videos = max(database.total_videos(), 1)
    progress = round(len(watched_ids) / total_videos, 2)
    recommended = youtube_service.recommended_videos_for_user(
        {
            "id": g.current_user.id,
            "email": g.current_user.email,
            "full_name": g.current_user.full_name,
            "city": g.current_user.city,
            "project_type": g.current_user.project_type,
        },
        projects,
        watched_ids,
    )
    hire_requests = database.list_hire_requests(user_id)

    return jsonify(
        {
            "success": True,
            "user": {
                "id": g.current_user.id,
                "email": g.current_user.email,
                "full_name": g.current_user.full_name,
                "city": g.current_user.city,
                "project_type": g.current_user.project_type,
            },
            "projects": projects,
            "progress": {
                "videos_watched": len(watched_ids),
                "total_videos": total_videos,
                "percentage": progress,
            },
            "recommended_videos": recommended,
            "hire_requests": hire_requests,
        }
    )


@api_bp.post("/projects")
@require_auth
def create_project() -> tuple[Response, int]:
    payload = request.get_json(force=True, silent=True) or {}
    project_data = validate_project_payload(payload)
    generated = plan_generator.generate_project_package(project_data)

    project_title = payload.get("title") or f"Proyecto {project_data['ciudad']}"
    user_id = g.current_user.id
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
    generated["success"] = True
    generated["message"] = "Proyecto generado correctamente"

    return jsonify(generated), HTTPStatus.CREATED


@api_bp.get("/projects/<int:project_id>")
@require_auth
def get_project(project_id: int) -> tuple[Response, int]:
    user_id = g.current_user.id
    project = database.get_user_project(project_id, user_id)
    if project is None:
        return jsonify({"success": False, "error": "Proyecto no encontrado"}), HTTPStatus.NOT_FOUND
    watched_ids = database.get_watched_video_ids(user_id)
    total_videos = max(database.total_videos(), 1)
    project["video_progress"] = round(len(watched_ids) / total_videos, 2)
    project["videos_watched"] = len(watched_ids)
    project["total_videos"] = total_videos
    manual = (project.get("plan_data") or {}).get("manual") or {}
    if "recommended_videos" not in manual:
        manual["recommended_videos"] = youtube_service.recommended_videos_for_project(
            project.get("form_data", {})
        )
        project.setdefault("plan_data", {})["manual"] = manual
    project["success"] = True
    return jsonify(project), HTTPStatus.OK


@api_bp.get("/projects/<int:project_id>/manual/pdf")
@require_auth
def download_manual(project_id: int):
    user_id = g.current_user.id
    project = database.get_user_project(project_id, user_id)
    if project is None:
        return jsonify({"success": False, "error": "Proyecto no encontrado"}), HTTPStatus.NOT_FOUND

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
    generated["success"] = True
    return jsonify(generated)


# ---------------------------------------------------------------------------
# Video library
# ---------------------------------------------------------------------------
VIDEO_LEVEL_ORDER = {"principiante": 0, "intermedio": 1, "avanzado": 2}
VIDEO_LEVEL_LABELS = {
    "principiante": "Nivel Fácil (Principiante)",
    "intermedio": "Nivel Intermedio",
    "avanzado": "Nivel Avanzado",
}


@api_bp.get("/videos")
@require_auth
def list_videos() -> Response:
    level_filter = (request.args.get("level") or "").lower() or None
    category = request.args.get("category")
    stage = request.args.get("stage")
    search = request.args.get("search")
    rows = database.list_videos(level=level_filter, category=category, stage=stage, search=search)
    watched_ids = database.get_watched_video_ids(g.current_user.id)

    videos = [Video.from_row(row) for row in rows]
    grouped: list[dict[str, Any]] = []
    for level_key in (level_filter,) if level_filter else VIDEO_LEVEL_ORDER.keys():
        level_videos = [video for video in videos if video.level.lower() == level_key]
        if not level_videos:
            continue
        level_videos.sort(key=lambda video: (VIDEO_LEVEL_ORDER.get(video.level.lower(), 99), video.title))
        grouped.append(
            {
                "level": level_key,
                "label": VIDEO_LEVEL_LABELS.get(level_key, level_key.title()),
                "videos": [
                    {
                        "id": video.id,
                        "title": video.title,
                        "url": video.url,
                        "watch_url": video.url,
                        "embed_url": video.embed_url,
                        "youtube_id": video.youtube_id,
                        "level": video.level,
                        "category": video.category,
                        "stage": video.stage,
                        "manual_step": video.manual_step,
                        "description": video.description,
                        "thumbnail": video.thumbnail_url,
                        "watched": video.id in watched_ids,
                    }
                    for video in level_videos
                ],
            }
        )

    return jsonify({"success": True, "videos": grouped})


@api_bp.post("/videos/<int:video_id>/watch")
@require_auth
def track_video(video_id: int) -> tuple[Response, int]:
    database.record_video_watch(g.current_user.id, video_id)
    watched = len(database.get_watched_video_ids(g.current_user.id))
    total = max(database.total_videos(), 1)
    progress = round(watched / total, 2)
    return (
        jsonify(
            {
                "success": True,
                "progress": progress,
                "watched": watched,
                "total": total,
            }
        ),
        HTTPStatus.CREATED,
    )


# ---------------------------------------------------------------------------
# Manual overview and marketplace utilities
# ---------------------------------------------------------------------------
@api_bp.get("/manual/steps")
@require_auth
def manual_steps() -> Response:
    level = request.args.get("level")
    steps = manual_builder.build_manual_steps(level_filter=level)
    return jsonify({"success": True, "steps": steps})


@api_bp.get("/marketplace/providers")
def list_marketplace_providers() -> Response:
    city = (request.args.get("city") or "").strip() or None
    provider_type = (request.args.get("type") or "").strip() or None
    price_min = request.args.get("min_price")
    price_max = request.args.get("max_price")

    def _to_float(value: str | None) -> float | None:
        if not value:
            return None
        try:
            return float(value)
        except ValueError:
            return None

    providers = [
        Provider.from_row(row)
        for row in database.list_providers(
            city=city,
            provider_type=provider_type,
            price_min=_to_float(price_min),
            price_max=_to_float(price_max),
        )
    ]

    return jsonify(
        {
            "success": True,
            "providers": [
                {
                    "id": provider.id,
                    "name": provider.name,
                    "type": provider.provider_type,
                    "specialty": provider.specialty,
                    "city": provider.city,
                    "locality": provider.locality,
                    "price_min": provider.price_min,
                    "price_max": provider.price_max,
                    "rating": provider.rating,
                    "description": provider.description,
                    "contact": provider.contact,
                    "portfolio_url": provider.portfolio_url,
                    "experience_years": provider.experience_years,
                }
                for provider in providers
            ],
        }
    )


@api_bp.post("/marketplace/hire")
@require_auth
def create_hire() -> tuple[Response, int]:
    payload = request.get_json(force=True, silent=True) or {}
    provider_id = payload.get("provider_id")
    project_id = payload.get("project_id")
    message = (payload.get("message") or "").strip() or None

    if not provider_id or not project_id:
        return (
            jsonify({"success": False, "error": "Debes seleccionar un proveedor y un proyecto"}),
            HTTPStatus.BAD_REQUEST,
        )

    provider = database.get_provider(int(provider_id))
    if not provider:
        return jsonify({"success": False, "error": "Proveedor no encontrado"}), HTTPStatus.NOT_FOUND

    project = database.get_user_project(int(project_id), g.current_user.id)
    if project is None:
        return jsonify({"success": False, "error": "Proyecto inválido"}), HTTPStatus.NOT_FOUND

    hire_id = database.create_hire_request(
        user_id=g.current_user.id,
        project_id=int(project_id),
        provider_id=int(provider_id),
        message=message,
    )

    return (
        jsonify(
            {
                "success": True,
                "hire_id": hire_id,
                "message": "Solicitud enviada al proveedor",
            }
        ),
        HTTPStatus.CREATED,
    )


@api_bp.get("/marketplace/hire")
@require_auth
def list_hires() -> Response:
    hires = database.list_hire_requests(g.current_user.id)
    return jsonify({"success": True, "requests": hires})


@api_bp.get("/marketplace/alerts")
def safety_alerts() -> Response:
    alerts = [
        "Utiliza señalización perimetral y cinta de peligro durante toda la obra.",
        "Verifica que el contratista cuente con equipo de seguridad personal (EPP).",
        "Coordina con vecinos horarios de obra para minimizar molestias.",
    ]
    return jsonify({"success": True, "alerts": alerts})


@api_bp.get("/testimonials")
def testimonials() -> Response:
    rows = database.fetch_rows("SELECT author, location, quote FROM testimonials")
    return jsonify({"success": True, "testimonials": rows})


@api_bp.get("/financing/products")
def financing_products() -> Response:
    product_type = request.args.get("type")
    products = financing.get_financing_products(product_type=product_type)
    return jsonify({"success": True, "products": products})


@api_bp.get("/financing/simulate")
def simulate_financing() -> Response:
    amount = float(request.args.get("amount", 0))
    months = int(request.args.get("months", 0))
    rate = float(request.args.get("rate", 0))
    simulation = financing.simulate_payment_plan(amount=amount, months=months, rate=rate)
    simulation["success"] = True
    return jsonify(simulation)


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------
@api_bp.errorhandler(ValueError)
def handle_validation_error(exc: ValueError) -> tuple[Response, int]:
    return jsonify({"success": False, "error": str(exc)}), HTTPStatus.BAD_REQUEST


@api_bp.errorhandler(Exception)
def handle_generic_error(exc: Exception) -> tuple[Response, int]:
    current_app.logger.exception("Unhandled error: %s", exc)
    return (
        jsonify({"success": False, "error": "Ocurrió un error inesperado"}),
        HTTPStatus.INTERNAL_SERVER_ERROR,
    )
