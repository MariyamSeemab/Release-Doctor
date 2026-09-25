"""Demo repository frontend — order details page.

PLANTED RISK 3: Breaking API response change.
This component still accesses `order.customer_name` which was removed
from the GET /api/orders/{order_id} response in the backend.
"""
import React, { useEffect, useState } from 'react';

interface Order {
  id: number;
  status: string;
  customer_name: string;  // ← PLANTED RISK 3: field removed from API response
  total: number;
  items: any[];
}

export function OrderDetail({ orderId }: { orderId: number }) {
  const [order, setOrder] = useState<Order | null>(null);

  useEffect(() => {
    fetch(`/api/orders/${orderId}`)
      .then(r => r.json())
      .then(data => setOrder(data));
  }, [orderId]);

  if (!order) return <div>Loading...</div>;

  return (
    <div className="order-detail">
      <h2>Order #{order.id}</h2>
      {/* This will render as undefined because customer_name was removed from the API */}
      <p>Customer: {order.customer_name}</p>
      <p>Status: {order.status}</p>
      <p>Total: ${order.total}</p>
    </div>
  );
}
