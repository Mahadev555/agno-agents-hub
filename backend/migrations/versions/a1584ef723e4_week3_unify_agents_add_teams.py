"""week3: unify agents, add teams

Collapses `host_agent` into `agents` behind a `kind` discriminator and promotes
teams to first-class entities.

This migration moves data, it does not just reshape tables:

  * agents.kind is backfilled from the old agent_type/is_mcp pair.
  * Every host_agent row is copied into agents with kind='host'. Ids collide
    between the two tables, so hosts get fresh ids and runs.host_agent_id is
    remapped to match.
  * host_agent.mode moves into the config blob, since orchestration mode is a
    property of a team rather than of the coordinator.
  * A team is seeded from each migrated host agent so existing coordinators
    remain usable through the new /api/teams endpoints.

Revision ID: a1584ef723e4
Revises:
Create Date: 2026-08-07 20:36:42.299425
"""

import json
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a1584ef723e4"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # ---- 1. agents.kind, backfilled before it becomes NOT NULL --------------
    op.add_column("agents", sa.Column("kind", sa.String(length=20), nullable=True))
    conn.execute(
        sa.text(
            """
            UPDATE agents
               SET kind = CASE
                            WHEN is_mcp IS TRUE THEN 'mcp'
                            WHEN agent_type = 'mcp' THEN 'mcp'
                            WHEN agent_type = 'host' THEN 'host'
                            ELSE 'simple'
                          END
            """
        )
    )
    op.alter_column("agents", "kind", nullable=False)
    op.create_index("ix_agents_kind", "agents", ["kind"])

    # ---- 2. move host_agent rows into agents -------------------------------
    # Ids overlap between the tables, so let the sequence assign new ones and
    # keep a mapping to fix up references.
    #
    # agent_type/is_mcp are still NOT NULL at this point (they are dropped in
    # step 6), so these inserts must still populate them.
    hosts = conn.execute(
        sa.text(
            """
            SELECT agent_id, name, description, is_active, mode, config,
                   created_at, updated_at
              FROM host_agent
             ORDER BY agent_id
            """
        )
    ).mappings().all()

    id_map = {}
    for host in hosts:
        config = dict(host["config"] or {})
        # mode used to be its own column; fold it in so nothing is lost.
        config.setdefault("mode", host["mode"] or "coordinate")
        config.setdefault("name", host["name"])

        # A name collision with an existing worker agent would violate the
        # unique constraint, so disambiguate rather than fail the migration.
        new_name = host["name"]
        collision = conn.execute(
            sa.text("SELECT 1 FROM agents WHERE name = :n"), {"n": new_name}
        ).scalar()
        if collision:
            new_name = f"{new_name} (host)"

        new_id = conn.execute(
            sa.text(
                """
                INSERT INTO agents
                    (name, description, kind, agent_type, is_mcp, is_active,
                     mcp_config, config, created_at, updated_at)
                VALUES
                    (:name, :description, 'host', 'host', FALSE, :is_active,
                     '{}'::jsonb, CAST(:config AS jsonb), :created_at, :updated_at)
                RETURNING agent_id
                """
            ),
            {
                "name": new_name,
                "description": host["description"],
                "is_active": True if host["is_active"] is None else host["is_active"],
                "config": json.dumps(config),
                "created_at": host["created_at"],
                "updated_at": host["updated_at"],
            },
        ).scalar()

        id_map[host["agent_id"]] = new_id

    # ---- 3. new tables ------------------------------------------------------
    op.create_table(
        "teams",
        sa.Column("team_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("host_agent_id", sa.Integer(), nullable=False),
        sa.Column("mode", sa.String(length=20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["host_agent_id"], ["agents.agent_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("team_id"),
    )
    op.create_index("ix_teams_created_at", "teams", ["created_at"])
    op.create_index("ix_teams_is_active", "teams", ["is_active"])
    op.create_index("ix_teams_name", "teams", ["name"], unique=True)

    op.create_table(
        "team_members",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("agent_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.agent_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["team_id"], ["teams.team_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("team_id", "agent_id", name="uq_team_agent"),
    )
    op.create_index("ix_team_members_agent_id", "team_members", ["agent_id"])
    op.create_index("ix_team_members_team_id", "team_members", ["team_id"])

    # ---- 4. seed a team per migrated host, with all workers as members ------
    worker_ids = [
        row[0]
        for row in conn.execute(
            sa.text(
                "SELECT agent_id FROM agents WHERE kind IN ('simple','mcp') ORDER BY agent_id"
            )
        ).all()
    ]

    for old_host_id, new_host_id in id_map.items():
        host = conn.execute(
            sa.text("SELECT name, description, config FROM agents WHERE agent_id = :i"),
            {"i": new_host_id},
        ).mappings().first()
        mode = (host["config"] or {}).get("mode", "coordinate")

        team_id = conn.execute(
            sa.text(
                """
                INSERT INTO teams
                    (name, description, host_agent_id, mode, is_active, config,
                     created_at, updated_at)
                VALUES
                    (:name, :description, :host_id, :mode, TRUE, '{}'::jsonb,
                     NOW(), NOW())
                RETURNING team_id
                """
            ),
            {
                "name": host["name"],
                "description": host["description"] or "Migrated from host_agent",
                "host_id": new_host_id,
                "mode": mode,
            },
        ).scalar()

        for position, agent_id in enumerate(worker_ids):
            conn.execute(
                sa.text(
                    """
                    INSERT INTO team_members (team_id, agent_id, position)
                    VALUES (:t, :a, :p)
                    """
                ),
                {"t": team_id, "a": agent_id, "p": position},
            )

    # ---- 5. repoint runs.host_agent_id at the new agent ids -----------------
    for old_id, new_id in id_map.items():
        conn.execute(
            sa.text("UPDATE runs SET host_agent_id = :new WHERE host_agent_id = :old"),
            {"new": new_id, "old": old_id},
        )

    # ---- 6. drop what has been replaced ------------------------------------
    op.drop_index("ix_host_agent_created_at", table_name="host_agent")
    op.drop_index("ix_host_agent_is_active", table_name="host_agent")
    op.drop_index("ix_host_agent_name", table_name="host_agent")
    op.drop_table("host_agent")

    op.drop_column("agents", "is_mcp")
    op.drop_column("agents", "agent_type")


def downgrade() -> None:
    conn = op.get_bind()

    # Recreate the old columns and backfill from kind.
    op.add_column("agents", sa.Column("agent_type", sa.String(length=50), nullable=True))
    op.add_column("agents", sa.Column("is_mcp", sa.Boolean(), nullable=True))
    conn.execute(
        sa.text(
            """
            UPDATE agents
               SET agent_type = kind,
                   is_mcp = (kind = 'mcp')
            """
        )
    )
    op.alter_column("agents", "agent_type", nullable=False)

    op.create_table(
        "host_agent",
        sa.Column("agent_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_mcp", sa.Boolean(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("mode", sa.String(length=50), nullable=True),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("agent_id"),
    )
    op.create_index("ix_host_agent_created_at", "host_agent", ["created_at"])
    op.create_index("ix_host_agent_is_active", "host_agent", ["is_active"])
    op.create_index("ix_host_agent_name", "host_agent", ["name"], unique=True)

    # Copy coordinators back out of agents.
    conn.execute(
        sa.text(
            """
            INSERT INTO host_agent
                (name, description, is_mcp, is_active, mode, config,
                 created_at, updated_at)
            SELECT name, description, FALSE, is_active,
                   COALESCE(config->>'mode', 'coordinate'), config,
                   created_at, updated_at
              FROM agents
             WHERE kind = 'host'
            """
        )
    )

    # teams.host_agent_id is ON DELETE RESTRICT, so the team tables must go
    # before the coordinator rows they point at.
    op.drop_index("ix_team_members_team_id", table_name="team_members")
    op.drop_index("ix_team_members_agent_id", table_name="team_members")
    op.drop_table("team_members")
    op.drop_index("ix_teams_name", table_name="teams")
    op.drop_index("ix_teams_is_active", table_name="teams")
    op.drop_index("ix_teams_created_at", table_name="teams")
    op.drop_table("teams")

    # runs.host_agent_id pointed at the merged ids; clear it rather than leave
    # references to agent rows that are about to disappear.
    conn.execute(
        sa.text(
            """
            UPDATE runs SET host_agent_id = NULL
             WHERE host_agent_id IN (SELECT agent_id FROM agents WHERE kind = 'host')
            """
        )
    )
    conn.execute(sa.text("DELETE FROM agents WHERE kind = 'host'"))

    op.drop_index("ix_agents_kind", table_name="agents")
    op.drop_column("agents", "kind")
