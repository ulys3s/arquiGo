"""API routes for ConstruyeSeguro."""
from __future__ import annotations

from http import HTTPStatus
from pathlib import Path
from flask import Blueprint, Response, current_app, jsonify, request, send_file

from . import database
from .services import financing, manual_builder, marketplace, plan_generator, youtube_service
from .validation import validate_project_payload

api_bp = Blueprint("api", __name__)


@api_bp.post("/projects")
def create_project() -> tuple[Response, int]:
    payload = request.get_json(force=True, silent=True) or {}
    data = validate_project_payload(payload)

    generated = plan_generator.generate_project_package(data)
    project_id = database.save_project(data, generated, generated["viability"]["score"])
    generated["project_id"] = project_id

    storage_dir: Path = current_app.config["PROJECT_STORAGE"]
    storage_dir.mkdir(parents=True, exist_ok=True)
    manual_builder.generate_manual_pdf(
        project_id=project_id,
        project_summary=generated,
        destination=storage_dir / f"manual_{project_id}.pdf",
    )

    return jsonify(generated), HTTPStatus.CREATED


@api_bp.get("/projects/<int:project_id>")
def get_project(project_id: int) -> tuple[Response, int]:
    project = database.get_project(project_id)
    if project is None:
        return jsonify({"error": "Proyecto no encontrado"}), HTTPStatus.NOT_FOUND
    return jsonify(project), HTTPStatus.OK


@api_bp.get("/projects/<int:project_id>/manual/pdf")
def download_manual(project_id: int):
    project = database.get_project(project_id)
    if project is None:
        return jsonify({"error": "Proyecto no encontrado"}), HTTPStatus.NOT_FOUND

    storage_dir: Path = current_app.config["PROJECT_STORAGE"]
    pdf_path = storage_dir / f"manual_{project_id}.pdf"
    if not pdf_path.exists():
        manual_builder.generate_manual_pdf(
            project_id=project_id,
            project_summary=project["results"],
            destination=pdf_path,
        )
    return send_file(pdf_path, download_name=f"manual_construyeseguro_{project_id}.pdf")


@api_bp.get("/videos")
def list_videos() -> Response:
    category = request.args.get("category")
    search = request.args.get("search")
    videos = youtube_service.list_videos(category=category, search=search)
    return jsonify({"videos": videos})


@api_bp.get("/manual/steps")
def manual_steps() -> Response:
    level = request.args.get("level")
    steps = manual_builder.build_manual_steps(level_filter=level)
    return jsonify({"steps": steps})


@api_bp.get("/marketplace/architects")
def list_architects() -> Response:
    city = request.args.get("city")
    specialty = request.args.get("specialty")
    architects = marketplace.get_architects(city=city, specialty=specialty)
    return jsonify({"architects": architects})


@api_bp.get("/marketplace/suppliers")
def list_suppliers() -> Response:
    city = request.args.get("city")
    material = request.args.get("material")
    suppliers = marketplace.get_suppliers(city=city, material=material)
    return jsonify({"suppliers": suppliers})


@api_bp.get("/marketplace/alerts")
def safety_alerts() -> Response:
    return jsonify({"alerts": marketplace.get_safety_alerts()})


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


@api_bp.get("/maps/suppliers")
def suppliers_map() -> Response:
    city = request.args.get("city")
    material = request.args.get("material")
    markers = marketplace.get_supplier_markers(city=city, material=material)
    return jsonify({"markers": markers})


@api_bp.errorhandler(ValueError)
def handle_validation_error(exc: ValueError) -> tuple[Response, int]:
    return jsonify({"error": str(exc)}), HTTPStatus.BAD_REQUEST


@api_bp.errorhandler(Exception)
def handle_generic_error(exc: Exception) -> tuple[Response, int]:
    current_app.logger.exception("Unhandled error: %s", exc)
    return jsonify({"error": "Ocurrió un error inesperado"}), HTTPStatus.INTERNAL_SERVER_ERROR
