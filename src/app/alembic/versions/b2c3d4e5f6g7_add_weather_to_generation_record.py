"""Add weather columns to WindFarmGenerationRecord.

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2026-01-03

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f6g7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add weather columns to windfarmgenerationrecord
    op.add_column('windfarmgenerationrecord',
                  sa.Column('wind_speed', sa.Float(), nullable=True,
                           comment='Average wind speed in m/s used for generation'))
    op.add_column('windfarmgenerationrecord',
                  sa.Column('wind_direction', sa.Float(), nullable=True,
                           comment='Wind direction in degrees'))
    op.add_column('windfarmgenerationrecord',
                  sa.Column('temperature', sa.Float(), nullable=True,
                           comment='Temperature in Celsius'))


def downgrade() -> None:
    op.drop_column('windfarmgenerationrecord', 'temperature')
    op.drop_column('windfarmgenerationrecord', 'wind_direction')
    op.drop_column('windfarmgenerationrecord', 'wind_speed')



