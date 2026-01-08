"""Add WindFarmGenerationRecord table, make wind_turbine_id nullable, add is_synthetic flag.

Revision ID: a1b2c3d4e5f6
Revises: fdf881ac9ce9
Create Date: 2026-01-03

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = "fdf881ac9ce9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create turbinestatusenum type
    turbine_status_enum = sa.Enum("on", "off", name="turbinestatusenum")
    turbine_status_enum.create(op.get_bind(), checkfirst=True)

    # Create windfarmgenerationrecord table
    op.create_table(
        "windfarmgenerationrecord",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("wind_farm_id", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("generation", sa.Float(), nullable=False),
        sa.Column(
            "granularity",
            sa.Enum(
                "min_1",
                "min_5",
                "min_15",
                "min_30",
                "min_60",
                name="granularityenum",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("fleet_statuses", sa.JSON(), nullable=False),
        sa.Column("is_synthetic", sa.Boolean(), nullable=False, server_default="false"),
        sa.ForeignKeyConstraint(
            ["wind_farm_id"],
            ["windfarm.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_windfarmgenerationrecord_timestamp"),
        "windfarmgenerationrecord",
        ["timestamp"],
        unique=False,
    )
    op.create_index(
        op.f("ix_windfarmgenerationrecord_wind_farm_id"),
        "windfarmgenerationrecord",
        ["wind_farm_id"],
        unique=False,
    )

    # Make wind_turbine_id nullable in windturbinegenerationrecord
    op.alter_column(
        "windturbinegenerationrecord",
        "wind_turbine_id",
        existing_type=sa.INTEGER(),
        nullable=True,
    )

    # Add is_synthetic column to windturbinegenerationrecord
    op.add_column(
        "windturbinegenerationrecord",
        sa.Column("is_synthetic", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    # Remove is_synthetic from windturbinegenerationrecord
    op.drop_column("windturbinegenerationrecord", "is_synthetic")

    # Make wind_turbine_id not nullable again
    op.alter_column(
        "windturbinegenerationrecord",
        "wind_turbine_id",
        existing_type=sa.INTEGER(),
        nullable=False,
    )

    op.drop_index(
        op.f("ix_windfarmgenerationrecord_wind_farm_id"),
        table_name="windfarmgenerationrecord",
    )
    op.drop_index(
        op.f("ix_windfarmgenerationrecord_timestamp"),
        table_name="windfarmgenerationrecord",
    )
    op.drop_table("windfarmgenerationrecord")

    # Drop turbinestatusenum type
    turbine_status_enum = sa.Enum("on", "off", name="turbinestatusenum")
    turbine_status_enum.drop(op.get_bind(), checkfirst=True)
