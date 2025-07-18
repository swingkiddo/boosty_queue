"""add slot_num to request model

Revision ID: 72fa7190fdcd
Revises: d61da1195320
Create Date: 2025-06-12 09:56:01.325083

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '72fa7190fdcd'
down_revision: Union[str, None] = 'd61da1195320'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('session_requests', sa.Column('slot_number', sa.Integer(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('session_requests', 'slot_number')
    # ### end Alembic commands ###
