"""add structured PDF extraction fields

Revision ID: 0002_extraction_fields
Revises: 0001_initial
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_extraction_fields"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    existing = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("investigations")}
    columns = {
        "manufacturing_date": sa.Column("manufacturing_date", sa.String(length=80), nullable=True),
        "department": sa.Column("department", sa.String(length=160), nullable=True),
        "incident_category": sa.Column("incident_category", sa.String(length=160), nullable=True),
        "batch_disposition": sa.Column("batch_disposition", sa.Text(), nullable=True),
    }
    for name, column in columns.items():
        if name not in existing:
            op.add_column("investigations", column)


def downgrade():
    existing = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("investigations")}
    for name in ("batch_disposition", "incident_category", "department", "manufacturing_date"):
        if name in existing:
            op.drop_column("investigations", name)
