"""Demo repository — test suite.

Clean baseline state (before the OrderFlow v2 feature branch).
Tests match the clean API surface: get_order and list_orders.
"""


def test_get_order():
    """Tests the order response shape."""
    response = {"id": 1, "status": "pending", "customer_name": "Alice", "total": 10.0}
    assert response["customer_name"] == "Alice"
    assert response["total"] == 10.0


def test_list_orders():
    """Basic list test."""
    orders = []
    assert isinstance(orders, list)
