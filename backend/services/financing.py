"""Financing helper functions."""
from __future__ import annotations

from typing import Any

from .. import database


def get_financing_products(product_type: str | None = None) -> list[dict[str, Any]]:
    query = (
        "SELECT name, provider, rate, term_months, product_type, requirements FROM financing_products"
    )
    params: list[str] = []

    if product_type:
        query += " WHERE product_type = ?"
        params.append(product_type)

    query += " ORDER BY rate ASC"
    return database.fetch_rows(query, params)


def simulate_payment_plan(amount: float, months: int, rate: float) -> dict[str, float]:
    if amount <= 0 or months <= 0:
        raise ValueError("Proporciona un monto y plazo válidos para la simulación")

    monthly_rate = rate / 100 / 12
    if monthly_rate == 0:
        payment = amount / months
    else:
        payment = amount * (monthly_rate * (1 + monthly_rate) ** months) / (
            (1 + monthly_rate) ** months - 1
        )
    total_paid = payment * months
    interest_paid = total_paid - amount
    return {
        "monthly_payment": round(payment, 2),
        "total_paid": round(total_paid, 2),
        "interest_paid": round(interest_paid, 2),
    }
