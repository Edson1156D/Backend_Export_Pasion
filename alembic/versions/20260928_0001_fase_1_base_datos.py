"""Create the Fase 1 database model without removing existing data.

Revision ID: 20260928_0001
Revises:
"""
from typing import Sequence, Union

from alembic import context, op
import sqlalchemy as sa
from sqlalchemy import inspect

from app.bd.seed import seed_catalogos


revision: str = "20260928_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(name: str) -> bool:
    if context.is_offline_mode():
        return False
    return inspect(op.get_bind()).has_table(name)


def upgrade() -> None:
    if not _table_exists("users"):
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("full_name", sa.String(255), nullable=False),
            sa.Column("email", sa.String(255), nullable=False),
            sa.Column("hashed_password", sa.String(255), nullable=False),
            sa.Column("role", sa.String(50), nullable=False, server_default="VENDEDOR"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )

    if not _table_exists("categories"):
        op.create_table(
            "categories",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("parent_id", sa.Integer(), sa.ForeignKey("categories.id", ondelete="RESTRICT")),
            sa.Column("name", sa.String(150), nullable=False),
            sa.Column("description", sa.Text()),
        )
    if not _table_exists("suppliers"):
        op.create_table(
            "suppliers",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(255), nullable=False),
        )
    if not _table_exists("foreign_partners"):
        op.create_table(
            "foreign_partners",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("country", sa.String(120), nullable=False),
        )
    if not _table_exists("products"):
        op.create_table(
            "products",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("category_id", sa.Integer(), sa.ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("sku", sa.String(50), nullable=False),
            sa.Column("name", sa.String(150), nullable=False),
            sa.Column("unit_type", sa.String(20), nullable=False),
            sa.Column("sale_price", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("cost_price", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("current_stock", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("min_stock_alert", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
    if not _table_exists("lots"):
        op.create_table(
            "lots",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("code", sa.String(50), nullable=False, unique=True),
            sa.Column("origin", sa.String(30), nullable=False),
            sa.Column("initial_qty", sa.Numeric(12, 2), nullable=False),
            sa.Column("available_qty", sa.Numeric(12, 2), nullable=False),
            sa.Column("unit_cost_pen", sa.Numeric(12, 2), nullable=False),
            sa.Column("supplier_id", sa.Integer(), sa.ForeignKey("suppliers.id", ondelete="RESTRICT")),
            sa.Column("foreign_partner_id", sa.Integer(), sa.ForeignKey("foreign_partners.id", ondelete="RESTRICT")),
            sa.Column("responsable_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("received_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
    if not _table_exists("stock_entries"):
        op.create_table(
            "stock_entries",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("quantity", sa.Numeric(12, 2), nullable=False),
            sa.Column("supplier_id", sa.Integer(), sa.ForeignKey("suppliers.id", ondelete="RESTRICT")),
            sa.Column("responsable_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("notes", sa.Text()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
    if not _table_exists("sales"):
        op.create_table(
            "sales",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("folio", sa.String(50), nullable=False, unique=True),
            sa.Column("sale_type", sa.String(30), nullable=False),
            sa.Column("payment_method", sa.String(30), nullable=False),
            sa.Column("subtotal", sa.Numeric(12, 2), nullable=False),
            sa.Column("total", sa.Numeric(12, 2), nullable=False),
            sa.Column("paid_with", sa.Numeric(12, 2)),
            sa.Column("change_amount", sa.Numeric(12, 2)),
            sa.Column("responsable_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
    if not _table_exists("sale_items"):
        op.create_table(
            "sale_items",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("sale_id", sa.Integer(), sa.ForeignKey("sales.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("name", sa.String(150), nullable=False),
            sa.Column("sku", sa.String(50), nullable=False),
            sa.Column("unit_type", sa.String(20), nullable=False),
            sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
            sa.Column("quantity", sa.Numeric(12, 2), nullable=False),
        )
    if not _table_exists("inventory_movements"):
        op.create_table(
            "inventory_movements",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("responsable_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("movement_type", sa.String(30), nullable=False),
            sa.Column("quantity", sa.Numeric(12, 2), nullable=False),
            sa.Column("reason", sa.Text()),
            sa.Column("unit_sold_price", sa.Numeric(12, 2)),
            sa.Column("unit_cost_price", sa.Numeric(12, 2)),
            sa.Column("waste_type", sa.String(100)),
            sa.Column("sale_group_id", sa.Integer(), sa.ForeignKey("sales.id", ondelete="RESTRICT")),
            sa.Column("supplier_name", sa.String(255)),
            sa.Column("folio", sa.String(50)),
            sa.Column("unit_price_usd", sa.Numeric(12, 2)),
            sa.Column("exchange_rate", sa.Numeric(10, 4)),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
    if not _table_exists("wastes"):
        op.create_table(
            "wastes",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("quantity", sa.Numeric(12, 2), nullable=False),
            sa.Column("reason_code", sa.String(100), nullable=False),
            sa.Column("detail", sa.Text()),
            sa.Column("responsable_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
    if not _table_exists("foreign_trade_operations"):
        op.create_table(
            "foreign_trade_operations",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("folio", sa.String(50), nullable=False, unique=True),
            sa.Column("date", sa.Date(), nullable=False),
            sa.Column("type", sa.String(20), nullable=False),
            sa.Column("partner_id", sa.Integer(), sa.ForeignKey("foreign_partners.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("incoterm", sa.String(10)),
            sa.Column("transport", sa.String(20)),
            sa.Column("exchange_rate", sa.Numeric(10, 4), nullable=False),
            sa.Column("subtotal_usd", sa.Numeric(12, 2), nullable=False),
            sa.Column("total_usd", sa.Numeric(12, 2), nullable=False),
            sa.Column("total_pen", sa.Numeric(12, 2), nullable=False),
            sa.Column("notes", sa.Text()),
            sa.Column("responsable_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
    if not _table_exists("foreign_trade_lines"):
        op.create_table(
            "foreign_trade_lines",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("operation_id", sa.Integer(), sa.ForeignKey("foreign_trade_operations.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("name", sa.String(150), nullable=False),
            sa.Column("sku", sa.String(50), nullable=False),
            sa.Column("unit_type", sa.String(20), nullable=False),
            sa.Column("quantity", sa.Numeric(12, 2), nullable=False),
            sa.Column("price_usd", sa.Numeric(12, 2), nullable=False),
            sa.Column("subtotal_usd", sa.Numeric(12, 2), nullable=False),
        )
    if not _table_exists("foreign_trade_counters"):
        op.create_table(
            "foreign_trade_counters",
            sa.Column("type", sa.String(20), primary_key=True),
            sa.Column("last_number", sa.Integer(), nullable=False, server_default="0"),
        )

    # No authoritative catalog rows exist in docs/schema.sql, so this is intentionally empty.
    if not context.is_offline_mode():
        seed_catalogos(op.get_bind())

    op.create_index("ix_users_email_lower", "users", [sa.text("lower(email)")], unique=True)
    op.create_index("ix_products_sku_lower", "products", [sa.text("lower(sku)")], unique=True)
    op.create_index("ix_lots_product_received_id", "lots", ["product_id", "received_at", "id"])
    op.create_index("ix_inventory_movements_created_at", "inventory_movements", ["created_at"])
    op.create_index("ix_sales_created_at", "sales", ["created_at"])


def downgrade() -> None:
    raise RuntimeError("Fase 1 no permite downgrade destructivo: la migracion agrega tablas y no debe borrar datos.")