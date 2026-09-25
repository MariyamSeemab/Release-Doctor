# OrderFlow API — Requirements Specification v1.2

## Overview
The OrderFlow API manages customer orders for the e-commerce platform.

## Endpoints

### GET /api/orders
Returns a list of all orders for the authenticated user.

### GET /api/orders/{order_id}
Returns details for a specific order.

**Response fields:**
- `id` (integer) — order ID
- `status` (string) — order status
- `customer_name` (string) — **name of the customer** ← PLANTED RISK 8: this field was removed from the actual API
- `total` (float) — order total
- `items` (array) — line items

### POST /api/orders
Create a new order. Requires authentication.

### DELETE /api/orders/{order_id}
Cancel an order. Requires authentication.

## Authentication
All write endpoints require a valid JWT Bearer token in the Authorization header.
Read endpoints require authentication for customer data.

## Notes
- The refund endpoint (`POST /api/orders/{order_id}/refund`) is NOT documented here
  because it was added without updating this specification. (PLANTED RISK 8)
- Priority-based order filtering via `min_priority` parameter is undocumented.
