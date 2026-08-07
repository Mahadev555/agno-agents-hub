# Architecture

Why the backend is shaped the way it is. For the API reference see [README.md](./README.md).

---

## The core idea

Agents are **data**. Their configuration lives in PostgreSQL as validated JSONB and is hydrated into live Agno objects at request time. Nothing is deployed to add an agent.

That only works if the boundary is respected in one direction:

```
schemas/   models/     <-- describe agents as data. Do NOT import agno.
runtime/   agents/     <-- the only layers that know Agno exists.
```

If the registry layer imported Agno, a change to `Team`'s signature would ripple into the database layer. Keeping the import one-way is what makes the framework replaceable.

---

## Request flow

### Creating an agent

```
POST /api/agents
  routes/            get_current_user -> 401 if no valid token
  controllers/       attach owner_id
  schemas/           AgentConfig validates: tools, model provider, unknown keys
  services/          uniqueness check, INSERT
```

Validation happens **here**, on write. An unknown tool name is a `400` at create time rather than a failure when someone runs the agent three days later.

### Running an agent

```
POST /api/runs
  routes/            authenticate
  controllers/run_   rate limit -> resolve composition -> INSERT run (pending)
                     -> open bus channel -> schedule asyncio task -> 202 {run_id}

  [background]       mark running
                     agents/subhost   build Agent or Team
                     runtime/         registries + MCP egress check
                     agno             arun(stream=True)
                     -> normalise events -> publish to bus -> UPDATE run (terminal)

GET /api/runs/{id}/events
  routes/            authenticate (header or ?access_token=)
  services/run_bus   replay buffer, then live events
```

The `202` returns before the work is done. Everything needed to reject a bad request — missing agent, no read access, over quota — is resolved *before* scheduling, so those are synchronous errors rather than something the client discovers over the event stream.

---

## Decisions worth knowing

### Execution is decoupled from the HTTP request

A coordinated team run is several sequential LLM calls and routinely takes 20-60s. When execution lived inside the request handler, a closed tab or a proxy timeout aborted work that had already spent tokens, and the client got nothing.

Now the run is an `asyncio` task with a durable row. The connection can drop at any point; the run finishes and the result is in the database.

*Cost:* a run in flight when the process dies can never finish. `RunService.reap_orphans()` closes those out at startup rather than leaving them stuck in `running` forever.

### One async path, no thread hopping

Everything from the route to `agno.arun()` is `async` on one event loop.

An earlier version wrapped execution in a synchronous `Workflow.run()` that spawned a thread and created a *new* event loop. MCP sessions were entered on the outer loop and used on the inner one, which is undefined behaviour — hangs, `Event loop is closed`, or leaked subprocesses.

MCP sessions are now entered into an `AsyncExitStack` **inside the same coroutine that runs the agent**, so they are always created and closed on the loop that uses them.

### Configuration is typed and validated on write

`config` was `Dict[str, Any]`, validated nowhere. Defaults were hand-patched in the HTTP layer with eight `if 'x' not in config` blocks, and the seeder bypassed that entirely — so the API and the seeder disagreed about what an agent looked like.

`schemas/agent_config.py` is now the single definition. `extra="forbid"` means a typo (`instuctions`) is an error rather than a silently ignored key.

The LLM section is stored under both `model` and `model_config`. `model_config` is a **reserved attribute name in Pydantic v2**, so the field is `model`; the legacy key is kept readable for existing rows and consumed unconditionally when parsing.

### Registries, not hardcoded maps

Tool and model lookups were dicts inside the agent factory where an unknown tool was **silently dropped** and an unknown model type **silently became Gemini**. An agent configured with a typo produced a working-looking agent that quietly did less than asked.

`runtime/registry.py` raises instead, and the config schema calls into it, so bad names are caught at save time.

Tools are registered as **factories, not instances** — otherwise every agent in the process shares one tool object.

### One `agents` table, discriminated by `kind`

`agents` and `host_agent` were separate tables with ~90% identical columns, duplicated services, duplicated controllers, and an `is_host` boolean threaded through the routes. A coordinator is an agent with a coordinating role.

`agent_type` and `is_mcp` remain in API responses, derived from `kind`, so existing clients keep working.

### Teams are a first-class entity

Composition used to be sent by the client on every request. That meant a team could not be named, saved, shared, or versioned, and any caller could compose arbitrary agents.

`teams` + `team_members` persist it. `mode` lives on the **team**, not the coordinator, because the same host can drive different teams differently.

`host_agent_id` is `ON DELETE RESTRICT`: deleting a coordinator that a team depends on returns `409` instead of leaving the team unrunnable. (This constraint has already prevented one accidental mass delete.)

### Ownership, and why hidden resources return 404

`owner_id` on agents, teams, and runs; `is_public` for marketplace visibility.

A resource the caller may not read returns **404, not 403**. A 403 confirms the id exists, which turns the endpoint into an enumeration oracle.

Public means **readable, never writable**. Sharing an agent must not let a stranger edit or delete it.

Rows created before auth have `owner_id IS NULL`. Those are readable by all but writable only by an administrator — treating them as unowned rather than as everyone's property.

### The run bus is in-process, deliberately

`services/run_bus.py` fans events out to SSE subscribers and keeps a bounded replay buffer, so a client that subscribes a moment after `POST /api/runs` still receives the whole run instead of joining mid-sentence.

It is in-memory and single-process. With multiple workers a client could subscribe to a worker that is not executing its run — which is why `WEB_CONCURRENCY=1` in the Dockerfile. Terminal state is always recoverable from the `runs` table regardless, and the SSE endpoint falls back to replaying it from the database when no channel exists.

Redis is the fix when horizontal scaling is needed.

### Schema belongs to Alembic

`create_all()` cannot `ALTER` an existing table. Leaving it in the startup path meant column changes were silently skipped while the app appeared healthy. `init_db()` now only verifies connectivity.

### Errors carry their cause

anyio task groups (used by the MCP client) wrap real failures in an `ExceptionGroup` whose `str()` is the useless `"unhandled errors in a TaskGroup (1 sub-exception)"`. `_describe_exception` unwraps it so the caller sees `ConnectError: All connection attempts failed`.

Status codes reflect fault: `400` for a bad configuration, `502` for an unreachable MCP server, `404` for anything the caller may not see, `429` when over quota.

---

## Known limits

| Limit | Consequence | Fix |
|---|---|---|
| In-process run bus | One worker only | Move to Redis |
| Tests share `DATABASE_URL` | Running pytest writes to the app's database | Separate test database |
| SSE token in query string | Appears in access logs | Single-use stream ticket |
| No refresh tokens | Users re-authenticate when the token expires | Refresh flow |
| `models/agents_model.py` | Dead code, unused since Week 1 | Delete |
| `test_agent.py` | Manual script, not a test | Delete or convert |

---

## Extending

**Add a tool**

```python
# runtime/registry.py
@register_tool("wikipedia")
def _wikipedia():
    from agno.tools.wikipedia import WikipediaTools
    return WikipediaTools()
```

It becomes valid in agent configs immediately, and invalid names keep failing on save.

**Add a model provider**

```python
@register_model("anthropic")
def _anthropic(model_id, max_tokens, extra, **_):
    from agno.models.anthropic import Claude
    return Claude(id=model_id, max_tokens=max_tokens, **extra)
```

**Change the schema**

```bash
# edit models/
python -m alembic revision --autogenerate -m "what changed"
# read the generated file — autogenerate mishandles NOT NULL defaults
# and emits drop_constraint(None, ...) which cannot run
python -m alembic upgrade head
```

Test `downgrade` before trusting a migration. Both migrations in this repo had ordering bugs that only surfaced on the round trip.
