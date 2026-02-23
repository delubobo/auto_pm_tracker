"""add_phase2_columns

Revision ID: 191200065746
Revises:
Create Date: 2026-02-23 03:51:42.798558

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "191200065746"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add the six new Phase 2 columns (additive — no table rebuild needed).
    #    render_as_batch=True is set in env.py so SQLite handles these as a
    #    CREATE/COPY/DROP/RENAME cycle under the hood.
    with op.batch_alter_table("tasks", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "predecessor_ids",
                sa.Text(),
                server_default="[]",
                nullable=False,
            )
        )
        batch_op.add_column(sa.Column("start_date", sa.String(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "percent_complete",
                sa.Float(),
                server_default="0.5",
                nullable=True,
            )
        )
        batch_op.add_column(sa.Column("project_id", sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "task_type",
                sa.String(),
                server_default="Task",
                nullable=False,
            )
        )
        batch_op.add_column(sa.Column("assignee", sa.String(), nullable=True))

    # 2. Backfill predecessor_ids from dependency_id.
    #    Any row that already has a dependency_id gets a single-element JSON
    #    array: e.g. dependency_id=3  →  predecessor_ids='[3]'
    #    Rows with no dependency stay at the server_default '[]'.
    op.execute(
        sa.text(
            """
            UPDATE tasks
            SET predecessor_ids = '[' || dependency_id || ']'
            WHERE dependency_id IS NOT NULL
            """
        )
    )


def downgrade() -> None:
    with op.batch_alter_table("tasks", schema=None) as batch_op:
        batch_op.drop_column("assignee")
        batch_op.drop_column("task_type")
        batch_op.drop_column("project_id")
        batch_op.drop_column("percent_complete")
        batch_op.drop_column("start_date")
        batch_op.drop_column("predecessor_ids")
