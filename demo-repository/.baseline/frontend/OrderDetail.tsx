// Demo repository frontend — order details page.
// Clean baseline state (before the OrderFlow v2 feature branch).
import React, { useEffect, useState } from 'react';

interface Order {
  id: number;
  status: string;
  customer_name: string;
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
      <p>Customer: {order.customer_name}</p>
      <p>Status: {order.status}</p>
      <p>Total: ${order.total}</p>
    </div>
  );
}
