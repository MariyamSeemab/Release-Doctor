"""Demo repository — backend application (FastAPI).

This is a realistic sample e-commerce order management API.
It deliberately contains 8 planted risks discoverable by the Release Doctor agents.
"""
from __future__ import annotations

import os
from fastapi import FastAPI

app = FastAPI(title="OrderFlow API", version="2.0.0")


@app.get("/health")
def health():
    return {"status": "ok"}


# ── Risk 3 (planted): Breaking API response change ──────────────────────────
# Old response included `customer_name` field; new response removes it.
# Frontend still expects `customer_name`.
@app.get("/api/orders/{order_id}")
def get_order(order_id: int):
    return {
        "id": order_id,
        "status": "pending",
        # "customer_name": "...",  # REMOVED — breaks frontend consumer
        "customer_id": 42,         # renamed field, breaking change
        "total": 99.99,
        "items": [],
    }


# ── Risk 4 (planted): New endpoint without authorization ────────────────────
# This endpoint was added without a `Depends(get_current_user)` guard.
@app.post("/api/orders/{order_id}/refund")
def refund_order(order_id: int, amount: float):
    """Process a refund — MISSING AUTH. Any caller can trigger a refund."""
    return {"refunded": amount, "order_id": order_id}


# ── Risk 1 (planted): New required DB field — no migration ──────────────────
# The `priority_score` field is used here but no migration exists.
@app.get("/api/orders")
def list_orders(min_priority: float = 0.0):
    db_url = os.environ.get("DATABASE_URL")
    # Uses the new `priority_score` column that has no migration
    return {"orders": [], "filter": {"min_priority": min_priority}}


# ── Risk 2 (planted): New env var referenced but not in deployment config ───
ANALYTICS_ENDPOINT = os.environ.get("ANALYTICS_SERVICE_URL")  # Not in docker-compose or .env.example

@app.post("/api/orders/{order_id}/track")
def track_order(order_id: int):
    """Track order analytics — uses ANALYTICS_SERVICE_URL not declared in deployment."""
    if not ANALYTICS_ENDPOINT:
        return {"tracked": False, "reason": "analytics service not configured"}
    return {"tracked": True, "endpoint": ANALYTICS_ENDPOINT}
