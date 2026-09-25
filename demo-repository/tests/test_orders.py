"""Demo repository — test suite.

PLANTED RISK 5: Missing integration/regression tests.
- No test for the new /api/orders/{id}/refund endpoint
- No test for the priority_score field
- No migration integration test
"""


def test_get_order():
    """Existing test — only tests the old response shape."""
    # This test would now FAIL because customer_name is removed
    # but it is not updated to match the new response
    response = {"id": 1, "status": "pending", "customer_name": "Alice", "total": 10.0}
    assert response["customer_name"] == "Alice"  # ← will fail against new API
    assert response["total"] == 10.0


def test_list_orders():
    """Basic list test — does NOT test priority_score filtering."""
    orders = []
    assert isinstance(orders, list)


# MISSING TESTS (planted risk 5):
# - test_refund_order_requires_auth  ← not written
# - test_refund_order_happy_path     ← not written
# - test_priority_score_filter       ← not written
# - test_migration_upgrade_downgrade ← not written
# - test_track_order_analytics       ← not written
