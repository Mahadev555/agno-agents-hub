# Agno Hub

A multi-tenant agent orchestration platform built on [FastAPI](https://fastapi.tiangolo.com), [React](https://react.dev), and the [Agno framework](https://github.com/agno-agi/agno).

Agents are **data, not code**: their configuration lives in PostgreSQL and is hydrated into live Agno objects at request time. That means agents can be created, edited, composed into teams, and shared through the API without deploying anything.

---

## What it does

- **Define agents** — name, role, instructions, tools, and model settings, validated on save
- **Compose teams** — a coordinator plus ordered members, saved as a reusable entity
- **Run and stream** — execution is decoupled from the HTTP request; output streams token by token over SSE
- **Track everything** — every run is recorded with status, output, token usage, and duration
- **Multi-user** — accounts, per-user ownership, and public/private visibility

---

## Architecture

```
Request  ->  routes/          HTTP surface, auth dependency
         ->  controllers/     authorization, orchestration
         ->  services/        business logic, persistence
         ->  models/          SQLAlchemy ORM

Execution ->  runtime/        tool + model registries, MCP egress guard
          ->  agents/hosts/   config -> live Agno Agent/Team
          ->  agents/subhost/ async execution, event streaming
```

Three ideas hold it together:

**The registry does not import Agno.** `schemas/` and `models/` describe agents as data. Only `runtime/` and `agents/` know Agno exists, so a framework change cannot ripple into the database layer.

**Execution is decoupled from the request.** `POST /api/runs` returns `202` immediately and the work continues server-side. A closed tab no longer discards a run that has already spent tokens.

**Configuration is validated on write.** An unknown tool, an unknown model provider, or a typo'd key is rejected when an agent is *saved*, not when someone runs it days later.

```
Agno-Hub/
├── backend/
│   ├── models/            # SQLAlchemy: User, Agent, Team, TeamMember, Run
│   ├── schemas/           # Typed AgentConfig / TeamConfig / ModelConfig
│   ├── runtime/           # Tool + model registries, MCP SSRF guard
│   ├── services/          # Auth, agents, teams, runs, rate limiting, event bus
│   ├── controllers/       # Request handling + authorization
│   ├── routes/routes.py   # API endpoints
│   ├── agents/
│   │   ├── hosts/         # Config -> Agno Agent/Team factory
│   │   ├── subhost/       # Async execution + event streaming
│   │   └── configs/       # Seed JSON for a fresh install
│   ├── migrations/        # Alembic
│   ├── tests/             # pytest (no API quota needed)
│   ├── config.py          # Typed settings, validated at boot
│   ├── dependencies.py    # get_current_user, ownership checks
│   └── Dockerfile
├── frontend/              # React + Vite (JavaScript)
└── docker-compose.yml
```

---

## Quick start

### 1. Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate        # macOS / Linux
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
```

Minimum to run locally:

```env
DATABASE_URL=postgresql://user:password@host/dbname
GOOGLE_API_KEY=your-gemini-api-key
```

See [`backend/.env.example`](backend/.env.example) for everything else. Two worth knowing now:

- `JWT_SECRET` — optional in development (a random key is generated per process, which signs everyone out on restart). **Required** when `ENVIRONMENT` is `production` or `staging`; the app refuses to boot without it.
- `MCP_ALLOWED_HOSTS` — MCP endpoints on loopback/private addresses are blocked by default. To run a local MCP server, set `MCP_ALLOWED_HOSTS=localhost:3001`.

### 3. Create the schema

```bash
python -m alembic upgrade head
```

Alembic owns the schema. The app does **not** call `create_all()`, because it cannot `ALTER` existing tables and would silently drift from the migration history.

Optionally load the sample agents:

```bash
python seed_database.py     # WARNING: drops and recreates all tables
```

### 4. Run

```bash
python run_server.py         # http://localhost:5000
```

### 5. Frontend

```bash
cd frontend
npm install
npm run dev                  # http://localhost:3000
```

### 6. Create the first account

Every endpoint except `/health` and `/api/auth/*` requires a bearer token. Open the app and register — **the first account created becomes an administrator.**

---

## Authentication and ownership

| Rule | Behavior |
|---|---|
| Anonymous request | `401` on everything except `/health`, `/api/auth/register`, `/api/auth/login` |
| Own resource | Full read and write |
| Public resource (`is_public: true`) | Readable by anyone signed in, **writable only by its owner** |
| Someone else's private resource | `404`, not `403` — ids cannot be probed |
| Pre-auth rows (`owner_id: null`) | Readable by all, writable only by an administrator |

Passwords are hashed with **Argon2id**. Tokens are JWTs with a pinned algorithm.

---

## API

Interactive docs: **http://localhost:5000/docs**

### Auth
```
POST   /api/auth/register       Create an account (first one is admin)
POST   /api/auth/login          Exchange credentials for a token
GET    /api/auth/me             The signed-in account
```

### Agents
```
GET    /api/agents              List visible agents
GET    /api/agents/active
GET    /api/agents/mcp
GET    /api/agents/type/{kind}  simple | mcp | host
GET    /api/agents/name/{name}
GET    /api/agents/{id}
POST   /api/agents              Create (config validated on write)
PUT    /api/agents/{id}
DELETE /api/agents/{id}
```

### Teams
```
GET    /api/teams
POST   /api/teams               { name, hostAgentId, memberAgentIds, mode }
GET    /api/teams/{id}
PUT    /api/teams/{id}          memberAgentIds replaces membership wholesale
DELETE /api/teams/{id}
POST   /api/teams/{id}/runs     Run a saved team
```

### Runs (streaming — preferred)
```
POST   /api/runs                202 { run_id }; work continues server-side
GET    /api/runs                Your run history
GET    /api/runs/{id}           One run record
GET    /api/runs/{id}/events    SSE: started | token | tool_call | completed | error
```

### Blocking execution (older, still supported)
```
POST   /api/chat
POST   /api/agent/run
POST   /api/team/run
```

These hold the connection open for the whole run. Prefer `/api/runs` — a coordinated team routinely takes 20-60s.

### Example

```bash
TOKEN=$(curl -s -X POST localhost:5000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"you@example.com","password":"your-passphrase"}' | jq -r .access_token)

RUN=$(curl -s -X POST localhost:5000/api/runs \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"prompt":"Research Zoho and summarise","agentIds":[3]}' | jq -r .run_id)

curl -N "localhost:5000/api/runs/$RUN/events?access_token=$TOKEN"
```

---

## Agent kinds

A single `agents` table holds all three, discriminated by `kind`:

- **`simple`** — a worker with registry-backed tools (e.g. `duckduckgo`)
- **`mcp`** — a worker backed by a Model Context Protocol server
- **`host`** — a coordinator that delegates to team members

Teams run in one of Agno's three modes: **`route`**, **`coordinate`**, or **`collaborate`**. Mode belongs to the *team*, not the coordinator, so one host can drive different teams differently.

---

## Configuration schema

Agent config is typed (`schemas/agent_config.py`) and rejects unknown keys:

```json
{
  "name": "Research Agent",
  "role": "Research Specialist",
  "instructions": ["Search thoroughly", "Cite sources"],
  "tools": ["duckduckgo"],
  "model": { "type": "google", "id": "gemini-2.5-flash-lite", "max_tokens": 2048 },
  "markdown": true,
  "show_tool_calls": true
}
```

The LLM section is also written as `model_config` for backward compatibility with older rows. New code should use `model` — `model_config` is a reserved attribute name in Pydantic v2.

Adding a tool means registering it in `runtime/registry.py`; it then becomes valid in configs automatically.

---

## Testing

```bash
cd backend
python -m pytest tests/ -v
```

59 tests covering streaming, run persistence, config validation, team rules, auth, authorization, SSRF, and rate limits. The LLM is stubbed, so **no API quota is consumed**.

> **Note:** tests currently run against `DATABASE_URL` — the same database the app uses. Point it at a scratch database before running them.

---

## Deployment

```bash
docker compose up --build
```

The image builds the React app and serves it from the API, so there is one artifact. It runs migrations on start, drops to a non-root user, and exposes a healthcheck.

`WEB_CONCURRENCY` is **1** by default: the run event bus is in-process, so an SSE subscriber must reach the worker executing its run. Scaling out requires moving the bus to Redis first (see `services/run_bus.py`).

---

## Limits worth knowing

- **Single-process event bus** — see above.
- **Rate limits** — `RUN_RATE_LIMIT_PER_HOUR` (default 60) and `RUN_CONCURRENCY_PER_USER` (default 3), enforced per account because runs cost real money.
- **SSE token in query string** — `EventSource` cannot set headers, so the SSE endpoint also accepts `?access_token=`. Query strings often appear in access logs; a single-use stream ticket would be stronger.
- **Gemini free tier** is 20 requests/day per model, which is easy to exhaust while testing.

---

## Stack

**Backend** — FastAPI, SQLAlchemy 2.0, Alembic, PostgreSQL (Neon), Pydantic v2, Agno 1.5.10, PyJWT, Argon2, Python 3.12
**Frontend** — React 19, Vite 5, Tailwind, Framer Motion, Axios (JavaScript, not TypeScript)
**Default model** — Gemini 2.5 Flash Lite; OpenAI and Azure OpenAI are also registered

---

## Documentation

- [Backend README](./backend/README.md) — API reference, schema, operations
- [Backend Architecture](./backend/ARCHITECTURE.md) — design decisions and request flow
- [Frontend README](./frontend/README.md) — components and data flow

---

Made with 🧠 ❤️ by **Mahadev Manerikar**
