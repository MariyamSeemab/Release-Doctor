"""Initial migration — creates customers, orders, order_items tables.

NOTE: This migration does NOT include the `priority_score` column
that was subsequently added to the Order model. This is intentional —
it represents the planted "missing migration" risk.
"""
from alembic import op
import sqlalchemy as sa


revision = "001_initial"
down_revision = None


def upgrade():
    op.create_table(
        "customers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
    )
    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("status", sa.String(50), default="pending"),
        sa.Column("total", sa.Float(), default=0.0),
        # NOTE: `priority_score` column is deliberately absent here
    )
    op.create_table(
        "order_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Float(), nullable=False),
    )


def downgrade():
    op.drop_table("order_items")
    op.drop_table("orders")
    op.drop_table("customers")
