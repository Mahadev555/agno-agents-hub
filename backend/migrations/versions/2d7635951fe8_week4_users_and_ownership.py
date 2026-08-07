"""week4: users and ownership

Adds accounts and attaches ownership to agents, teams, and runs.

Existing rows keep owner_id = NULL. They are deliberately not assigned to an
arbitrary account: an unowned row is treated as administrator-only by
dependencies.require_owner, and the first registered user is an admin, so a
fresh deployment can still manage its seeded agents.

Note on NOT NULL columns: is_public needs a server_default, otherwise adding it
to a table that already has rows fails. The default is dropped afterwards so the
application layer stays responsible for the value on new rows.

Revision ID: 2d7635951fe8
Revises: a1584ef723e4
Create Date: 2026-08-07
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "2d7635951fe8"
down_revision: Union[str, Sequence[str], None] = "a1584ef723e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Named explicitly so downgrade can drop them; autogenerate emits None here,
# which cannot be dropped.
FK_AGENTS_OWNER = "fk_agents_owner_id_users"
FK_TEAMS_OWNER = "fk_teams_owner_id_users"
FK_RUNS_OWNER = "fk_runs_owner_id_users"


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("user_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_admin", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_index("ix_users_created_at", "users", ["created_at"])
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_is_active", "users", ["is_active"])

    # ---- agents ----
    op.add_column("agents", sa.Column("owner_id", sa.Integer(), nullable=True))
    op.add_column(
        "agents",
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column("agents", "is_public", server_default=None)
    op.create_index("ix_agents_owner_id", "agents", ["owner_id"])
    op.create_index("ix_agents_is_public", "agents", ["is_public"])
    op.create_foreign_key(
        FK_AGENTS_OWNER, "agents", "users", ["owner_id"], ["user_id"], ondelete="CASCADE"
    )

    # ---- teams ----
    op.add_column("teams", sa.Column("owner_id", sa.Integer(), nullable=True))
    op.add_column(
        "teams",
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column("teams", "is_public", server_default=None)
    op.create_index("ix_teams_owner_id", "teams", ["owner_id"])
    op.create_index("ix_teams_is_public", "teams", ["is_public"])
    op.create_foreign_key(
        FK_TEAMS_OWNER, "teams", "users", ["owner_id"], ["user_id"], ondelete="CASCADE"
    )

    # ---- runs ----
    op.add_column("runs", sa.Column("owner_id", sa.Integer(), nullable=True))
    op.create_index("ix_runs_owner_id", "runs", ["owner_id"])
    op.create_foreign_key(
        FK_RUNS_OWNER, "runs", "users", ["owner_id"], ["user_id"], ondelete="CASCADE"
    )


def downgrade() -> None:
    op.drop_constraint(FK_RUNS_OWNER, "runs", type_="foreignkey")
    op.drop_index("ix_runs_owner_id", table_name="runs")
    op.drop_column("runs", "owner_id")

    op.drop_constraint(FK_TEAMS_OWNER, "teams", type_="foreignkey")
    op.drop_index("ix_teams_is_public", table_name="teams")
    op.drop_index("ix_teams_owner_id", table_name="teams")
    op.drop_column("teams", "is_public")
    op.drop_column("teams", "owner_id")

    op.drop_constraint(FK_AGENTS_OWNER, "agents", type_="foreignkey")
    op.drop_index("ix_agents_is_public", table_name="agents")
    op.drop_index("ix_agents_owner_id", table_name="agents")
    op.drop_column("agents", "is_public")
    op.drop_column("agents", "owner_id")

    op.drop_index("ix_users_is_active", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_created_at", table_name="users")
    op.drop_table("users")
