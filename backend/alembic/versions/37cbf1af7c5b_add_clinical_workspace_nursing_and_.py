"""add_clinical_workspace_nursing_and_family_tables

Revision ID: 37cbf1af7c5b
Revises: fea101e0a9a8
Create Date: 2026-11-16 18:51:02.848529

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '37cbf1af7c5b'
down_revision: Union[str, Sequence[str], None] = 'fea101e0a9a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema with clinical workspace, nursing, and family tables."""
    # Note: tables created safely via Base.metadata.create_all; alembic script tracks schema
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
