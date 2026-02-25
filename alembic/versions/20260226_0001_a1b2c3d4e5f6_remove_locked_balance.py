"""remove locked_balance from wallets (closed coin economy)

Revision ID: a1b2c3d4e5f6
Revises: cfd62feace54
Create Date: 2026-02-26

Rationale:
  Aurex operates a closed coin economy — no withdrawals, no TDS, no payout system.
  locked_balance was intended to hold coins during active room participation but was
  never written to in practice (always 0). Removing it simplifies the wallet model
  and removes any implication of a withdrawal-ready system.

Safe to apply on live data: column is always 0, no data loss occurs.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'a1b2c3d4e5f6'
down_revision = 'cfd62feace54'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop locked_balance — always 0, no data loss
    op.drop_column('wallets', 'locked_balance')


def downgrade() -> None:
    # Restore the column with default 0 if you ever need to roll back
    op.add_column(
        'wallets',
        sa.Column(
            'locked_balance',
            sa.Integer(),
            nullable=False,
            server_default='0',
        )
    )
