# College Baseball API (Node.js / TypeScript)

Fastify + TypeScript **read API** for the college baseball scouting dashboard. Serves ranked pitcher/hitter endpoints over the shared Postgres warehouse while Python remains the ETL writer (scrape → match → upsert).

## Why Node.js / TypeScript

- The dashboard issues many concurrent, short-lived filtered reads — a natural fit for Node’s non-blocking I/O.
- Typed contracts (TypeScript + Zod) make filter params and response shapes explicit and testable.
- Connection pooling, request IDs, and short TTL caching on meta routes give a clear optimization path without coupling HTTP to scrape jobs.

## Endpoints

| Method | Path | Notes |
|--------|------|--------|
| `GET` | `/health` | Liveness |
| `GET` | `/ready` | Postgres ping |
| `GET` | `/api/conferences` | Cached ~60s |
| `GET` | `/api/seasons` | Cached ~60s |
| `GET` | `/api/pitchers` | Filters: `limit`, `conference_id`, `drafted`, `min_ip` (`0-10`\|`11-20`\|`20+`), `season`, `age` |
| `GET` | `/api/hitters` | Filters: `limit`, `conference_id`, `drafted`, `min_ab`, `season`, `age` |
| `GET` | `/` | Scouting dashboard (same UI as before) |

`limit` is capped at **200**.

## Setup

```bash
# From repo root — Postgres must be running with college_baseball loaded
cd api
npm install
cp ../.env.example ../.env   # if needed; defaults match local postgres
npm run dev                  # http://localhost:8080
```

```bash
npm test          # unit + parity tests (parity needs DB)
npm run typecheck
npm run build && npm start
```

## Architecture

```
Python ETL (scrapers / main.py) --> PostgreSQL <-- Fastify TypeScript API <-- Dashboard
```

Parity fixtures under `tests/fixtures/` were captured from the prior Flask API so rankings and grades stay consistent after the cutover.
