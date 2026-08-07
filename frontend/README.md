# Agno Hub — Frontend

React single-page app for creating agents, composing teams, and running them with live streamed output.

For the project overview see the [root README](../README.md); for the API see the [backend README](../backend/README.md).

> **JavaScript, not TypeScript.** Source files are `.jsx`. An earlier version of this document described a TypeScript app with a different file layout; that app does not exist.

---

## Layout

```
frontend/
├── index.html               Vite entry HTML
├── vite.config.js           Dev server on :3000, /api proxy to :5000
├── tailwind.config.js
├── postcss.config.js
├── src/
│   ├── main.jsx             React root
│   ├── App.jsx              Auth gate + tab shell
│   ├── index.css            Tailwind + shared classes
│   ├── components/
│   │   ├── Login.jsx        Sign in / register
│   │   ├── Header.jsx       Top bar, account menu, sign out
│   │   ├── Sidebar.jsx      Navigation + create-agent modal
│   │   ├── Dashboard.jsx    Counts and overview
│   │   ├── AgentComponent.jsx  Agent cards
│   │   ├── ChatPlayground.jsx  Run agents/teams with streamed output
│   │   ├── Settings.jsx
│   │   ├── Button.jsx
│   │   └── index.js
│   ├── hooks/
│   │   ├── useMediaQuery.js
│   │   └── index.js
│   └── services/
│       └── api.js           HTTP client, auth, SSE
└── public/
```

---

## Setup

```bash
npm install
npm run dev        # http://localhost:3000
```

The backend must be running on `http://localhost:5000`.

| Script | Does |
|---|---|
| `npm run dev` | Vite dev server with HMR |
| `npm run build` | Production build to `dist/` |
| `npm run preview` | Serve the built output |
| `npm run lint` | ESLint over `src` |

### Configuration

`.env`:

```env
VITE_API_URL=http://localhost:5000
```

Because this is an absolute URL, requests go **directly** to the API and bypass the Vite proxy — so they are cross-origin and CORS applies. The backend must list this app's origin in `CORS_ALLOW_ORIGINS`; `http://localhost:3000` is included by default.

Leave `VITE_API_URL` unset to use the `/api` proxy in `vite.config.js` instead, which makes requests same-origin.

---

## Authentication

Every API endpoint except `/health` and `/api/auth/*` requires a bearer token, so `App.jsx` gates the whole UI:

```
App mounts
  -> token in localStorage?  no  -> <Login />
                             yes -> GET /api/auth/me
                                      ok   -> render the app
                                      401  -> clear token, <Login />
```

`services/api.js` owns the mechanics:

- **`tokenStore`** — reads/writes `agnohub.token` in `localStorage`
- **request interceptor** — attaches `Authorization: Bearer <token>` to everything
- **response interceptor** — on `401`, clears the token and notifies the app so it drops to the login screen instead of rendering empty lists
- **`setUnauthenticatedHandler`** — how `App.jsx` subscribes to that

The first account registered on a fresh deployment becomes an **administrator**.

> The token is in `localStorage`, which any script on the page can read — it is only as safe as the app's XSS posture. `httpOnly` cookies would be stronger but need CSRF handling and a same-site deployment.

---

## Running agents

`ChatPlayground.jsx` uses the streaming API. Both single-agent and team modes go through one path:

```js
const run = await runService.start(prompt, { agentIds, hostAgentId })

runService.stream(run.run_id, {
  onEvent: (e) => { if (e.type === 'token') append(e.text) },
  onDone:  (e) => finalize(e.output),
  onError: (err) => showError(err.message),
})
```

`POST /api/runs` returns immediately and the server keeps working regardless of what this client does; tokens then arrive over SSE and render into a placeholder message as they come.

Two details that matter:

**`EventSource` cannot set headers**, so the token goes in the query string (`?access_token=`). The backend accepts either.

**The stream is closed explicitly** on a terminal event. `EventSource` reconnects automatically when a server closes a stream, which would replay the entire run.

### Error handling

The API returns FastAPI error bodies where `detail` is a string for raised errors and an **array of objects** for `422` validation failures. `extractErrorMessage` flattens both:

```
404 -> "Agent IDs not found: [999]"
502 -> "Could not connect to an MCP server ... Check that the MCP endpoint is running."
422 -> "prompt: String should have at least 1 character"
429 -> "Run limit reached: 60 runs per hour. Try again later."
```

Rendering the raw `422` array would crash React on an object child.

A `200` response can also carry `status: "error"` when a run failed partway; `unwrapExecution` turns that into a thrown error rather than an empty reply.

### Timeouts

| Call type | Timeout | Why |
|---|---|---|
| CRUD | 15s | Should be fast; fail early |
| Execution | 300s | A team run is several sequential LLM calls |

A single 30s timeout used to abort real team runs client-side while the backend kept spending tokens.

---

## API client

`services/api.js` exports three services.

**`authService`** — `register`, `login`, `me`, `logout`, `hasToken`

**`agentService`** — `getAgents`, `getHostAgents`, `getAgentById`, `createAgent`, and the blocking `executeSingleAgent` / `executeTeam` / `sendMessage`

**`runService`** — `start`, `get`, `list`, `stream`

Prefer `runService` for execution. The `agentService.execute*` methods hold the connection open for the whole run and give no progress.

Responses identify agents by **`agent_id`** (FastAPI serialises by alias), and teams by `team_id`.

---

## Not yet wired

The backend supports these; the UI does not use them yet:

- **Teams** — `/api/teams` CRUD and `POST /api/teams/{id}/runs`. The playground still composes teams ad hoc each run instead of saving them.
- **Run history** — `GET /api/runs` returns the signed-in user's past runs with output, token usage, and duration.
- **Agent editing** — `PUT` and `DELETE /api/agents/{id}` have no UI.
- **Public agents** — `is_public` can be set on create but is not surfaced or filterable.

---

## Stack

React 19 · Vite 5 · Tailwind CSS 3 · Framer Motion · lucide-react · react-markdown · Axios

There are no tests. `npm run lint` is the only automated check.
