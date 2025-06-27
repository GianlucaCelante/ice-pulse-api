# alembic/versions/006_create_reports_table.py
"""006_create_reports_table

Revision ID: 006
Revises: 005
Create Date: 2025-06-19 15:00:00.000000

Adds reports table for HACCP compliance reporting
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # La tabella sarà creata automaticamente dai modelli SQLAlchemy
    pass

def downgrade() -> None:
    pass