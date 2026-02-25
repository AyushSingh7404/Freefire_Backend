"""add coin_packages table

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-02-26

Creates the coin_packages table used by:
  - GET /coin-packages          (public — frontend fetches for wallet + navbar shop)
  - POST /admin/coin-packages   (admin creates packages)
  - PUT  /admin/coin-packages/{id}
  - DELETE /admin/coin-packages/{id}  (soft-deactivate only)
  - POST /wallet/payment/initiate     (resolves price by package_id — never trusts FE amount)

Fields:
  id          — UUID PK
  coins       — coins the user receives on purchase (integer)
  price_inr   — price in Indian Rupees (integer — no floats in monetary values)
  is_active   — only active packages shown to users; deactivated = hidden but not deleted
  is_popular  — shows "Popular" badge in UI
  sort_order  — controls display order (ascending); lower = shown first
  created_at  — audit timestamp

Initial seed data (6 packages matching the existing COIN_PACKAGES constant):
  100 coins / ₹80
  310 coins / ₹250
  520 coins / ₹400 (Popular)
  1060 coins / ₹800
  2180 coins / ₹1600
  5600 coins / ₹4000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'coin_packages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('coins', sa.Integer(), nullable=False),
        sa.Column('price_inr', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('is_popular', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('sort_order', sa.Integer(), server_default='0', nullable=False),
        sa.Column(
            'created_at',
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
    )

    # ── Seed default packages ──────────────────────────────────────────────
    # These match the COIN_PACKAGES constant that was previously hardcoded
    # in wallet.component.ts. After this migration, the frontend reads from
    # the database — admin can change packages without a deployment.
    op.bulk_insert(
        sa.table(
            'coin_packages',
            sa.column('id',         postgresql.UUID(as_uuid=True)),
            sa.column('coins',      sa.Integer()),
            sa.column('price_inr',  sa.Integer()),
            sa.column('is_active',  sa.Boolean()),
            sa.column('is_popular', sa.Boolean()),
            sa.column('sort_order', sa.Integer()),
        ),
        [
            {'id': uuid.uuid4(), 'coins':  100, 'price_inr':   80, 'is_active': True, 'is_popular': False, 'sort_order': 0},
            {'id': uuid.uuid4(), 'coins':  310, 'price_inr':  250, 'is_active': True, 'is_popular': False, 'sort_order': 1},
            {'id': uuid.uuid4(), 'coins':  520, 'price_inr':  400, 'is_active': True, 'is_popular': True,  'sort_order': 2},
            {'id': uuid.uuid4(), 'coins': 1060, 'price_inr':  800, 'is_active': True, 'is_popular': False, 'sort_order': 3},
            {'id': uuid.uuid4(), 'coins': 2180, 'price_inr': 1600, 'is_active': True, 'is_popular': False, 'sort_order': 4},
            {'id': uuid.uuid4(), 'coins': 5600, 'price_inr': 4000, 'is_active': True, 'is_popular': False, 'sort_order': 5},
        ],
    )


def downgrade() -> None:
    op.drop_table('coin_packages')
