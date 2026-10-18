# Fish Seed Distribution — Backend API

REST API for fish-seed trips. It covers customer demand, supplier lists,
supplier slips, handovers to customers, stock-left, and trip close.

Stack: Python 3.14, FastAPI, SQLAlchemy, Alembic, PostgreSQL, uv, pytest, Ruff.

This repo holds the backend only. The React frontend lives in a separate repo.

## Requirements

- Python 3.14
- [uv](https://docs.astral.sh/uv/)
- PostgreSQL 14 or newer

## Setup

1. Clone and enter the repo.

```bash
   git clone git@github.com:danishskh70/fish-project.git
   cd fish-project
```

2. Install dependencies.

```bash
   uv sync
```

3. Create the database and user.

```bash
   sudo -u postgres createuser --pwprompt fish_app
   sudo -u postgres createdb -O fish_app fish_distribution
```

4. Create `.env` from the example. Put the real password in it.

```bash
   cp .env.example .env
```

5. Apply migrations.

```bash
   uv run alembic upgrade head
```

6. Run the server.

```bash
   uv run uvicorn main:app --reload
```

- API docs: http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/api/health

## Environment variables

Read from `.env` by `app/core/config.py`.

| Name | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string, for example `postgresql+psycopg://fish_app:PASSWORD@localhost:5432/fish_distribution` |

Never commit `.env`. It is in `.gitignore`.

## Checks

```bash
uv run pytest -q
uv run ruff check .
uv run alembic heads
```

- `alembic heads` must print exactly one head.
- Most tests use in-memory SQLite.
- PostgreSQL migration tests are skipped when no PostgreSQL test database is reachable.

## Project layout

| Path | Purpose |
|---|---|
| `main.py` | App entry point. Registers routers under `/api`. |
| `app/api` | HTTP routers. |
| `app/core` | Generic record engine: spec, service, router factory. |
| `app/specs` | Resource specs for fish types, customers, suppliers. |
| `app/models` | SQLAlchemy models. |
| `app/schemas` | Pydantic request and response schemas. |
| `app/services` | Business logic for trips, slips, handovers, stock, close. |
| `migrations` | Alembic revisions. |
| `tests` | pytest suite. |
| `docs` | Requirements, architecture, build plan, completed work. |

Master data (fish types, customers, suppliers) uses the generic record engine.
Trip workflows use custom routers and services.

## Trip lifecycle

`PLANNING` → `IN_PROGRESS` → `CLOSED`

- The first supplier slip sets `IN_PROGRESS`.
- `POST /api/trips/{id}/close` needs `IN_PROGRESS`.
- Close is blocked with 409 while any fish type has stock left above zero.
- Leftover fish is handed over to a customer named `Self`. Then close.
- Over-handover (negative stock) is allowed and flagged. It does not block close.
- A closed trip rejects new slips and handovers with 409.
- Close sets `closed_at` and returns the trip, final stock, and customer totals.

## Main endpoints (under `/api`)

| Path | Purpose |
|---|---|
| `/fish-types`, `/customers`, `/suppliers` | Master data |
| `/trips` | Create, list, detail |
| `/trips/{id}/customers` | Assign customers to a trip |
| `/trips/{id}/customers/{customer_id}/requirements` | Customer demand |
| `/trips/{id}/requirements-table` | Demand vs plan |
| `/trips/{id}/supplier-lists/...` | Supplier list draft, edit, finalize |
| `/trips/{id}/packing-list/...` | Packing list |
| `/trips/{id}/supplier-deliveries` | Supplier slips |
| `/trips/{id}/handovers` | Record and list handovers |
| `/trips/{id}/stock` | Slip bags, handed bags, left bags per fish type |
| `/trips/{id}/handover-totals` | Bags per customer and fish type |
| `/trips/{id}/close` | Close the trip |

Full list and schemas at `/docs` and `/openapi.json`.

## Example flow

```bash
# assign a customer to trip 2
curl -X POST http://127.0.0.1:8000/api/trips/2/customers \
  -H "Content-Type: application/json" -d '{"customer_id":3}'

# record a supplier slip (trip becomes IN_PROGRESS)
curl -X POST http://127.0.0.1:8000/api/trips/2/supplier-deliveries \
  -H "Content-Type: application/json" \
  -d '{"items":[{"fish_type_id":1,"delivered_bags":10}]}'

# hand over bags (trip_customer_id comes from the assign response)
curl -X POST http://127.0.0.1:8000/api/trips/2/handovers \
  -H "Content-Type: application/json" \
  -d '{"trip_customer_id":5,"submit_reference":"ref-1","lines":[{"fish_type_id":1,"bags":10}]}'

# close
curl -X POST http://127.0.0.1:8000/api/trips/2/close
```

`submit_reference` must be unique per handover. Resending the same reference
with the same data returns the original handover with 200. Different data
returns 409.

## For frontend developers

- Dev base URL: `http://127.0.0.1:8000/api`
- CORS is not enabled yet. Use a dev-server proxy to `/api`, or ask for CORS to be added.
- No authentication yet.
- Error bodies are `{"detail": "..."}`.
- Handover and slip writes are transactional. A failed request saves nothing.

## Status

Built:
- master data
- trips and customer assignment
- customer requirements
- supplier lists
- packing list
- supplier slips
- handovers
- stock-left
- trip close

Not built:
- authentication
- meeting points
- handover reversal
- returns and defects
- delivery draft and confirmation
- rates and billing
- payments
- reconciliation
- trip locking and versions
- reports

See `docs/BUILD_PLAN.md` for the plan and `docs/COMPLETED_WORK.md` for the record.

## Known limits

- Trip status values are `PLANNING`, `IN_PROGRESS`, `CLOSED`. The long-term design in `docs/REQUIREMENTS.md` uses more states.
- Retrying an old handover after the trip closes returns 409, not the original record.
- Trips created before the lifecycle change stay `PLANNING` even if they hold slips.