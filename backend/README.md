# Agno Hub — Backend

FastAPI service that stores agent definitions in PostgreSQL and executes them through the [Agno framework](https://github.com/agno-agi/agno).

For design rationale see [ARCHITECTURE.md](./ARCHITECTURE.md). For the project overview see the [root README](../README.md).

---

## Layout

```
backend/
├── app.py                  FastAPI app, CORS, SPA serving, lifespan
├── config.py               Typed settings; validated at boot
├── connection.py           Engine, session factory, session_scope()
├── dependencies.py         get_current_user, can_read, require_owner
├── logging_config.py       Logging configured once, here
├── run_server.py           Development entrypoint
├── seed_database.py        Load sample agents from JSON
│
├── models/                 SQLAlchemy
│   ├── base.py             Shared Base + utcnow()
│   ├── user.py             User
│   ├── agent.py            Agent, Team, TeamMember, AgentKind
│   └── run.py              Run, RunStatus
│
├── schemas/agent_config.py Typed AgentConfig / TeamConfig / ModelConfig
│
├── runtime/
│   ├── registry.py         Tool + model provider registries
│   └── mcp_guard.py        MCP egress policy (SSRF protection)
│
├── services/
│   ├── auth_service.py     Argon2 hashing, JWT issue/verify
│   ├── agent_service.py    Agent + Team writes (validated)
│   ├── database_service.py Reads
│   ├── run_service.py      Run persistence
│   ├── run_bus.py          In-process event fan-out for SSE
│   └── rate_limit.py       Per-user run quotas
│
├── controllers/            Authorization + orchestration
├── routes/routes.py        Endpoints
├── agents/
│   ├── hosts/host_agent.py Config -> Agno Agent/Team
│   ├── subhost/agent.py    Async execution + event streaming
│   └── configs/            Seed JSON
├── migrations/             Alembic
└── tests/                  pytest
```

---

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate               # Windows
source .venv/bin/activate             # macOS / Linux
pip install -r requirements.txt

cp .env.example .env                  # then fill in DATABASE_URL + GOOGLE_API_KEY
python -m alembic upgrade head        # create the schema
python run_server.py                  # http://localhost:5000
```

Register the first account through the API or the UI — **it becomes an administrator**.

### Optional: sample agents

```bash
python seed_database.py               # additive; skips agents that already exist
python seed_database.py --reset       # DESTRUCTIVE: drops every table first
```

`--reset` deletes users, teams, and run history as well as agents. It prompts for confirmation and refuses to run when `ENVIRONMENT` is `production` or `staging`.

---

## Database

Schema is managed by **Alembic**. The app does not call `create_all()` — it cannot `ALTER` existing tables, so relying on it would silently skip column changes and drift from the migration history.

```bash
python -m alembic upgrade head              # apply
python -m alembic revision --autogenerate -m "message"
python -m alembic downgrade -1              # roll back one
python -m alembic current                   # where am I
```

> Autogenerate gets two things wrong routinely: adding a `NOT NULL` column without a `server_default` fails on tables that already have rows, and it emits `drop_constraint(None, ...)` which cannot run. Name constraints explicitly and read the generated file before applying it.

### Tables

**`users`** — `user_id`, `email` (unique), `password_hash` (Argon2id), `display_name`, `is_active`, `is_admin`, `created_at`, `last_login_at`

**`agents`** — one table for workers *and* coordinators
| Column | Notes |
|---|---|
| `agent_id` | PK |
| `name` | unique |
| `kind` | `simple` \| `mcp` \| `host` |
| `owner_id` | FK users, nullable (pre-auth rows) |
| `is_public` | readable by all, writable only by owner |
| `is_active` | |
| `mcp_config` | JSONB — url, transport, timeout |
| `config` | JSONB — validated `AgentConfig` / `TeamConfig` |

`agent_type` and `is_mcp` are **derived** in API responses from `kind`; they are no longer columns.

**`teams`** — `team_id`, `name`, `host_agent_id` (FK agents, `ON DELETE RESTRICT`), `mode`, `owner_id`, `is_public`, `config`
**`team_members`** — `team_id`, `agent_id`, `position`; unique on `(team_id, agent_id)`
**`runs`** — `run_id` (uuid), `status`, `mode`, `prompt`, `output`, `error`, `agent_ids` (JSONB), `host_agent_id`, `owner_id`, token counts, `created_at` / `started_at` / `finished_at`, `duration_ms`

---

## Agent configuration

Validated by `schemas/agent_config.py`. Unknown keys are **rejected**, so a typo like `instuctions` fails on save instead of producing an agent that quietly ignores its instructions.

```json
{
  "name": "Research Agent",
  "description": "Conducts web research",
  "role": "Research Specialist",
  "instructions": ["Search thoroughly", "Cite sources"],
  "tools": ["duckduckgo"],
  "model": {
    "type": "google",
    "id": "gemini-2.5-flash-lite",
    "max_tokens": 2048
  },
  "markdown": true,
  "show_tool_calls": true
}
```

- `instructions` accepts a string or a list; it is normalised to a list.
- The LLM section is written under both `model` and `model_config`. Use `model` — `model_config` is a reserved attribute name in Pydantic v2 and is only kept for older rows.
- `schema_version` is stamped on every stored config.

### Registries

`runtime/registry.py` is the single place capability is declared.

```python
@register_tool("duckduckgo")
def _duckduckgo():
    from agno.tools.duckduckgo import DuckDuckGoTools
    return DuckDuckGoTools()
```

Registered tools: `duckduckgo`. Registered model providers: `google`, `openai`, `azure`.

Names are validated when an agent is **saved**. An unknown tool or provider is a `400` at create time, not a surprise at run time.

---

## API

Interactive docs at `/docs`. All endpoints require `Authorization: Bearer <token>` except `/health` and `/api/auth/{register,login}`.

### Auth
| Method | Path | Notes |
|---|---|---|
| POST | `/api/auth/register` | First account becomes admin |
| POST | `/api/auth/login` | Returns token + user |
| GET | `/api/auth/me` | Current account |

### Agents
| Method | Path |
|---|---|
| GET | `/api/agents`, `/api/agents/active`, `/api/agents/mcp` |
| GET | `/api/agents/type/{kind}`, `/api/agents/name/{name}`, `/api/agents/{id}` |
| POST | `/api/agents` |
| PUT | `/api/agents/{id}` |
| DELETE | `/api/agents/{id}` |

### Host agents (coordinators)
`GET /api/host-agents`, `GET /api/host-agents/{id}`, `POST /api/host-agents`

Kept for compatibility. Coordinators are `agents` rows with `kind='host'`.

### Teams
| Method | Path | Notes |
|---|---|---|
| GET | `/api/teams` | |
| POST | `/api/teams` | `{ name, hostAgentId, memberAgentIds, mode }` |
| GET | `/api/teams/{id}` | |
| PUT | `/api/teams/{id}` | `memberAgentIds` replaces membership wholesale |
| DELETE | `/api/teams/{id}` | Members cascade; agents remain |
| POST | `/api/teams/{id}/runs` | Run a saved team |

### Runs
| Method | Path | Notes |
|---|---|---|
| POST | `/api/runs` | `202 { run_id }`, work continues server-side |
| GET | `/api/runs` | Your history; `?limit=`, `?status=` |
| GET | `/api/runs/{id}` | |
| GET | `/api/runs/{id}/events` | SSE |

SSE event shape — deliberately provider-agnostic, so the contract survives Agno renaming its own events:

```
{"type": "started",   "mode": "team", "name": "...", "agents": [...]}
{"type": "token",     "text": "..."}
{"type": "tool_call", "status": "started", "name": "duckduckgo_search"}
{"type": "completed", "output": "...", "usage": {...}}
{"type": "error",     "message": "..."}
```

A terminal event (`completed` or `error`) is **always** last, so a consumer never has to infer the end.

### Blocking execution
`POST /api/chat`, `POST /api/agent/run`, `POST /api/team/run` — hold the connection for the whole run. Prefer `/api/runs`.

---

## Authorization

| Situation | Result |
|---|---|
| No token | `401` |
| Own resource | Read + write |
| Public resource | Read by anyone signed in; write only by owner (`403`) |
| Another user's private resource | `404` — ids cannot be probed |
| `owner_id IS NULL` (pre-auth) | Read by all; write admin-only |
| Another user's run | `404`, including its SSE stream |

---

## Security

**Passwords** — Argon2id. Not bcrypt, which silently truncates at 72 bytes and would make two long passphrases interchangeable.

**Tokens** — JWT with a pinned algorithm, so a token cannot request `alg: none`. The user is re-read from the database each request, so a disabled account stops working immediately.

**MCP egress** — an agent's `mcp_config.url` is user-supplied and the server connects to it, which is SSRF by design. `runtime/mcp_guard.py` resolves the host and refuses loopback, private, link-local, reserved, and multicast addresses — including `169.254.169.254`, where cloud instance metadata lives. Every resolved address is checked, since a hostname can resolve to both a public and a private address.

To use a local MCP server:
```env
MCP_ALLOWED_HOSTS=localhost:3001
```

**Rate limits** — runs are the only endpoint that spends money, so limits are counted there: `RUN_RATE_LIMIT_PER_HOUR` (from the `runs` table, so it survives restarts) and `RUN_CONCURRENCY_PER_USER` (in-process). Over-limit returns `429` with `Retry-After`.

---

## Configuration

All settings live in `config.py` and are validated at boot. See [`.env.example`](./.env.example).

| Variable | Default | Notes |
|---|---|---|
| `DATABASE_URL` | — | required |
| `GOOGLE_API_KEY` | — | required for Gemini |
| `JWT_SECRET` | random per process | **required** in production/staging |
| `ACCESS_TOKEN_TTL_MINUTES` | 720 | |
| `ALLOW_REGISTRATION` | true | set false once your users exist |
| `ENVIRONMENT` | development | development \| staging \| production \| test |
| `CORS_ALLOW_ORIGINS` | localhost:5173, localhost:3000 | must include your frontend origin |
| `MCP_ALLOWED_HOSTS` | *(empty)* | hosts exempt from the egress policy |
| `RUN_RATE_LIMIT_PER_HOUR` | 60 | |
| `RUN_CONCURRENCY_PER_USER` | 3 | |
| `DB_POOL_SIZE` / `DB_MAX_OVERFLOW` / `DB_POOL_RECYCLE` | 5 / 10 / 280 | |

---

## Testing

```bash
python -m pytest tests/ -v
```

59 tests. The LLM is stubbed via a fake runnable, so everything else runs for real — event normalisation, the run bus and its replay buffer, the SSE endpoint over ASGI, and run persistence — **without consuming API quota**.

> Tests currently use `DATABASE_URL`, the same database the app uses. Point it at a scratch database before running them.

---

## Deployment

```bash
docker compose up --build
```

The image builds the frontend and serves it from the API. Migrations run on start; the process drops to a non-root user.

`WEB_CONCURRENCY=1` is deliberate: `run_bus` is in-process, so an SSE subscriber must reach the worker executing its run. Moving the bus to Redis is the prerequisite for more workers.

---

## Troubleshooting

**`401` on everything** — every endpoint needs a bearer token now. Register or log in first.

**`relation "agents" does not exist`** — run `python -m alembic upgrade head`.

**`JWT_SECRET must be set`** — you set `ENVIRONMENT=production` without a secret. Generate one:
```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

**MCP agent returns `502` "not permitted"** — the egress guard blocked a private address. Add the host to `MCP_ALLOWED_HOSTS`.

**MCP agent returns `502` "connection attempts failed"** — the MCP server itself is not running.

**`429 Too Many Requests` from Gemini** — the free tier allows 20 requests per day per model. Unrelated to the app's own rate limits, which return a `Retry-After` header.

**CORS errors in the browser** — add your frontend origin to `CORS_ALLOW_ORIGINS`. A `*` wildcard disables credentials, per the CORS spec.
