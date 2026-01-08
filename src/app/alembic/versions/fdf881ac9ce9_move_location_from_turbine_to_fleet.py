"""Move location from turbine to fleet.

Revision ID: fdf881ac9ce9
Revises: 923bd7bcc78e
Create Date: 2026-01-01

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "fdf881ac9ce9"
down_revision: str | None = "923bd7bcc78e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add location_id to windturbinefleet
    op.add_column(
        "windturbinefleet", sa.Column("location_id", sa.Integer(), nullable=True)
    )

    # First, set a default location for existing fleets (use the turbine's location)
    # This is a data migration step
    op.execute("""
        UPDATE windturbinefleet
        SET location_id = windturbine.location_id
        FROM windturbine
        WHERE windturbinefleet.wind_turbine_id = windturbine.id
    """)

    # Make location_id not nullable after data migration
    op.alter_column("windturbinefleet", "location_id", nullable=False)

    # Add foreign key constraint
    op.create_foreign_key(
        "fk_windturbinefleet_location",
        "windturbinefleet",
        "location",
        ["location_id"],
        ["id"],
    )

    # Remove location_id from windturbine
    op.drop_constraint(
        "windturbine_location_id_fkey", "windturbine", type_="foreignkey"
    )
    op.drop_column("windturbine", "location_id")


def downgrade() -> None:
    # Add location_id back to windturbine
    op.add_column("windturbine", sa.Column("location_id", sa.Integer(), nullable=True))

    # Copy location from fleet back to turbine (take first one if multiple)
    op.execute("""
        UPDATE windturbine
        SET location_id = (
            SELECT windturbinefleet.location_id
            FROM windturbinefleet
            WHERE windturbinefleet.wind_turbine_id = windturbine.id
            LIMIT 1
        )
    """)

    # If there are turbines without fleets, set a default location
    op.execute("""
        UPDATE windturbine
        SET location_id = (SELECT id FROM location LIMIT 1)
        WHERE location_id IS NULL
    """)

    # Make it not nullable
    op.alter_column("windturbine", "location_id", nullable=False)

    # Add foreign key
    op.create_foreign_key(
        "windturbine_location_id_fkey",
        "windturbine",
        "location",
        ["location_id"],
        ["id"],
    )

    # Remove from fleet
    op.drop_constraint(
        "fk_windturbinefleet_location", "windturbinefleet", type_="foreignkey"
    )
    op.drop_column("windturbinefleet", "location_id")
