"""Add owner_id to tasks table

Revision ID: adefe187d7d5
Revises: 1adb5d22292b
Create Date: 2026-04-01 17:28:50.912650

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'adefe187d7d5'
down_revision: Union[str, Sequence[str], None] = '1adb5d22292b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('tasks', sa.Column('owner_id', sa.Integer(), nullable=False))
    op.create_foreign_key('tasks_users_fk', source_table='tasks', referent_table='users', local_cols=['owner_id'], remote_cols=['id'], ondelete='CASCADE')
    pass


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('tasks_users_fk', table_name='tasks', type_='foreignkey')
    op.drop_column('tasks', 'owner_id')
    pass
