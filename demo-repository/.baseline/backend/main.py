"""Demo repository — backend application (FastAPI).

This is a realistic sample e-commerce order management API.
Clean baseline state (before the OrderFlow v2 feature branch).
"""
from __future__ import annotations

from fastapi import FastAPI

app = FastAPI(title="OrderFlow API", version="1.0.0")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/orders/{order_id}")
def get_order(order_id: int):
    return {
        "id": order_id,
        "status": "pending",
        "customer_name": "Acme Corp",
        "total": 99.99,
        "items": [],
    }


@app.get("/api/orders")
def list_orders():
    return {"orders": []}
