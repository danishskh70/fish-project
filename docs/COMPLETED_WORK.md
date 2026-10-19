# Fish Seed Distribution — Completed Work Record

**Document purpose:** A start-to-finish record of what has been built so far, how the generic record engine works, how routers are created from resource specifications, and what is verified versus still planned.

**Project directory:** `~/projects/fish-project`  
**Stack:** Python, FastAPI, Pydantic, SQLAlchemy, PostgreSQL, Alembic, `uv`, pytest, Ruff  
**Last reported verification:** Ruff passed; 73 tests passed; Alembic reported `5cf800408ce3 (head)`.

---

## 1. Project purpose

This project is a backend for a fish-seed distribution workflow. It manages master data and trip-related records so that later features can support trip planning, supplier requirements, delivery, billing, payments, stock reconciliation, and trip completion.

The implementation has deliberately been built in stages. The current work establishes a reusable foundation for ordinary master-data operations while retaining custom APIs for trip workflows that have relationships or business-specific behavior.

### Main architecture decision

The project uses two approaches, chosen according to the kind of operation:

1. **Generic record engine** for master records whose common CRUD behavior can be shared.
2. **Custom routers and services** for trip operations and relationships that have their own business rules.

The goal is not to force every endpoint into one generic CRUD pattern. The goal is to remove repetitive master-data code without hiding domain-specific behavior.

---

## 2. Technology and project setup

The project uses:

- **FastAPI** for HTTP routes and API documentation.
- **Pydantic** for request and response validation.
- **SQLAlchemy** for ORM models and database operations.
- **PostgreSQL** as the development database.
- **Alembic** for schema migrations.
- **uv** for Python dependency and environment management.
- **pytest** and **HTTPX/TestClient** for tests.
- **Ruff** for linting.
- **Git** for version control.

The project declares Python `>=3.14` in `pyproject.toml`.

Useful project commands:

```bash
cd ~/projects/fish-project

# Run the API (if the project entry point is app.main:app)
uv run uvicorn app.main:app --reload

# Run tests
uv run pytest -q

# Run lint checks
uv run ruff check

# Check whitespace errors in tracked changes
git diff --check

# Show the current Alembic head
uv run alembic heads
```

Use the project's actual configured application entry point if it differs from the example Uvicorn command above.

---

## 3. High-level folder responsibilities

```text
fish-project/
├── app/
│   ├── api/
│   │   ├── customers.py
│   │   ├── fish_types.py
│   │   ├── suppliers.py
│   │   ├── trips.py
│   │   ├── trip_customers.py
│   │   ├── trip_customer_requirements.py
│   │   └── deps.py
│   ├── core/
│   │   ├── record_spec.py
│   │   ├── record_service.py
│   │   └── record_router.py
│   ├── db/
│   │   └── session.py
│   ├── models/
│   ├── schemas/
│   ├── services/
│   └── specs/
├── migrations/
│   ├── env.py
│   └── versions/
├── tests/
├── main.py
├── pyproject.toml
└── uv.lock
```

The tree is a responsibility guide rather than an exhaustive inventory of every file.

### `app/models/`

SQLAlchemy models describe database entities and their columns/relationships.

### `app/schemas/`

Pydantic schemas describe what the API accepts and returns. They form the HTTP validation/serialization boundary; they are not the database tables themselves.

### `app/api/`

Routers expose HTTP endpoints. The master-record API modules configure the generic router. Trip-related API modules retain custom endpoints for trip operations and relationships.

### `app/services/`

Contains domain-specific service logic that remains useful for custom operations, such as trip behavior. The former standalone customer, fish-type, and supplier service modules were removed as part of the generic-engine refactor because their shared master-record behavior moved into the generic service.

### `app/core/`

Contains the reusable record-engine components: specification, service, and router factory.

### `app/specs/`

Contains resource-specific `RecordSpec` definitions. A spec tells the generic engine which model and fields belong to a resource and which operations it exposes.

### `app/db/session.py`

Owns shared SQLAlchemy database setup, including the base used by ORM models and session configuration.

### `migrations/`

Alembic environment and version files describe database schema changes. Migration revision identifiers and parent links form the migration history.

### `tests/`

Automated tests cover API behavior and business operations. The last reported test run passed all 73 tests.

---

## 4. The generic record engine

The central pattern is:

```text
Resource-specific RecordSpec
           │
           ▼
RecordService(db, spec)
           │
           ▼
make_record_router(spec, service_class)
           │
           ▼
FastAPI routes for that resource
```

The three core files have different jobs.

### 4.1 `app/core/record_spec.py` — describe the resource

`RecordSpec` is configuration/metadata for one kind of record. Instead of writing a complete router separately for fish types, customers, and suppliers, each resource supplies a specification describing its model, fields, sorting, searching, and enabled operations.

The fish-type spec is in `app/specs/fish_type.py`. The verified spec reported:

```text
Resource key: fish-types
Database table: fish_types
Search fields: ('name',)
Sort fields: ('id', 'name', 'is_active')
Operations: activate, create, deactivate, list, update
```

The project later added generic deletion, so the current resource specs also enable `delete`.

A `FieldSpec` describes field-level behavior, such as:

- field name;
- human-readable label;
- whether it appears in list responses;
- whether it is searchable;
- whether it can be edited through generic update behavior.

A `RecordSpec` describes resource-level behavior, including:

- resource key and display title;
- SQLAlchemy model;
- collection of field specifications;
- default ordering;
- permitted sort fields;
- enabled operations.

The important design principle is that resource differences should be expressed in the specification when they are genuinely configuration differences. A spec should not be used to conceal a workflow that requires custom business logic.

### 4.2 `app/core/record_service.py` — perform database operations

`RecordService` contains the common database behavior. It is initialized with a SQLAlchemy session and a resource spec:

```python
service = RecordService(db, spec)
```

It derives the ORM model from the spec. That lets the same methods work for different resource types.

The implemented responsibilities include:

#### List records

`list_records(...)`:

1. Receives optional sort field, sort order, and search term.
2. Checks that the requested sort field is allowed by the spec.
3. Falls back to the spec's default ordering when the requested field is not permitted.
4. Applies ascending or descending order.
5. Searches only fields marked as searchable in the spec.
6. Escapes backslash, `%`, and `_` in user search text before using `ILIKE`, so those characters are treated literally rather than accidentally acting as SQL wildcard patterns.
7. Executes the SQLAlchemy query and returns the records.

This is important because a client must not be allowed to sort by arbitrary ORM attributes.

#### Get one record

`get_record(record_id)` uses the session to retrieve a record by primary key. It returns the record when found and `None` when no record exists. The router/service operation decides how that absence should be reported to the client.

#### Create a record

`create_record(data)`:

1. Converts the validated Pydantic data to a dictionary using `model_dump()`.
2. Creates the model specified by the resource spec.
3. Adds it to the session.
4. Commits the transaction.
5. On a SQLAlchemy `IntegrityError`, rolls back and raises the generic `RecordConflictError`.
6. Refreshes the created record so database-generated values are available.
7. Returns the created record.

The service does not need separate handwritten create logic for each master-record type.

#### Update a record

`update_record(record_id, data)`:

1. Finds the existing record.
2. Raises `RecordNotFoundError` if it does not exist.
3. Uses `model_dump(exclude_unset=True, exclude_none=True)` to identify supplied non-null changes.
4. Builds the allowed editable-field set from fields marked `editable=True` in the spec.
5. Applies only supplied changes that are allowed by the spec.
6. Raises `EmptyRecordUpdateError` if no editable changes remain.
7. Commits, rolls back on an integrity conflict, refreshes, and returns the updated record.

This separates request validation from the generic service's rule about which fields it may change.

#### Activate/deactivate a record

`set_active(record_id, is_active)`:

1. Loads the record.
2. Raises `RecordNotFoundError` if absent.
3. Checks that the model supports an `is_active` attribute.
4. Sets the flag.
5. Commits and refreshes the record.
6. Rolls back and raises `RecordConflictError` if a database constraint fails.

This is a soft-status operation: it changes the record's active state rather than deleting the row.

#### Delete a record

`delete_record(record_id)`:

1. Loads the record.
2. Raises `RecordNotFoundError` if absent.
3. Deletes the ORM object and commits.
4. If a foreign-key or other database integrity constraint prevents deletion, rolls back and raises `RecordConflictError`.

This is a hard delete. It is different from deactivation. A referenced record may not be deletable, depending on the database's constraints.

### 4.3 Generic service errors

The generic service defines these domain-level exceptions:

- `RecordNotFoundError`: the requested record does not exist.
- `RecordConflictError`: a database constraint prevents the operation.
- `EmptyRecordUpdateError`: no editable change was provided.

The service raises these exceptions without deciding the HTTP response. The router translates them into appropriate HTTP status codes and messages. This keeps the database layer reusable outside a particular HTTP endpoint.

---

## 5. `app/core/record_router.py` — how the router factory works

This is the key file that removes repetitive route definitions.

A FastAPI router is normally created by writing `@router.get`, `@router.post`, `@router.patch`, and similar functions manually for each resource. With three master-data resources, this would repeat much of the same code.

`make_record_router(spec, service_class)` creates a router from a resource specification and a service class.

Conceptually:

```python
router = make_record_router(
    FISH_TYPE,
    RecordService,
)
```

The exact import and variable names depend on each resource module, but the architecture is the same.

### 5.1 Router construction

The factory:

1. Receives the resource spec and service class.
2. Creates a FastAPI `APIRouter`.
3. Checks `spec.operations` to determine which route handlers to register.
4. For each enabled operation, defines the corresponding handler and attaches it to the router.
5. Uses the resource's schemas and service methods.
6. Returns the completed router.

The key point is that the operation checks happen when the router is constructed. If an operation is not enabled in the spec, that route is not registered for that resource.

### 5.2 Request lifecycle

A typical request travels through this sequence:

```text
HTTP request
    │
    ▼
FastAPI matches the registered route
    │
    ▼
FastAPI validates path, query and request-body data
    │
    ▼
get_db dependency provides a SQLAlchemy Session
    │
    ▼
Router creates service_class(db, spec)
    │
    ▼
Service performs the requested database operation
    │
    ├── success ──► router returns data/status
    │
    └── known error ──► router translates exception to HTTP error
    │
    ▼
FastAPI serializes the response using the response schema
```

`Depends(get_db)` is FastAPI's dependency-injection mechanism for supplying a database session to the route handler. It avoids manually opening a database session in every request handler.

The service is constructed with the session and the spec so that its behavior is connected to the current resource.

### 5.3 List route

The list handler accepts the supported list options, such as sorting and search, and calls the service's `list_records(...)`.

The spec determines which fields are valid for sorting and searching. This is why the same generic list route can safely serve multiple record types with different searchable/sortable fields.

### 5.4 Get route

When enabled, the get handler uses `get_record(record_id)`. If no record exists, the router responds with HTTP `404 Not Found`; otherwise it returns the record using the resource's read schema.

### 5.5 Create route

When enabled, the create handler accepts the resource's create schema and calls `create_record(...)`.

The router converts `RecordConflictError` to HTTP `409 Conflict`, for example when a unique constraint rejects a duplicate name. A successful creation returns HTTP `201 Created` and the created resource.

### 5.6 Update route

When enabled, the update handler accepts the update schema and calls `update_record(...)`.

The router translates:

- `RecordNotFoundError` to `404 Not Found`;
- `RecordConflictError` to `409 Conflict`;
- `EmptyRecordUpdateError` to the configured client-error response for an empty/non-editable update.

The read schema controls the response shape.

### 5.7 Activate and deactivate routes

When enabled, the factory registers the corresponding active-state routes and calls `set_active(...)` with the appropriate boolean.

Missing records return `404`. Database conflicts return `409`.

### 5.8 Delete route

When `"delete"` is present in `spec.operations`, the factory registers:

```text
DELETE /{record_id}
```

The handler calls `service.delete_record(record_id)`.

The configured behavior is:

- `204 No Content` when deletion succeeds;
- `404 Not Found` when the record does not exist;
- `409 Conflict` when a database integrity constraint prevents deletion.

A `204` response has no response body. This was exercised in an HTTP test: a fish type was created and deleting its ID returned `HTTP/1.1 204 No Content`.

### 5.9 Why `spec.operations` matters

The operations set acts as a small capability list for the resource. It controls which common actions the generic router exposes.

For example, a resource that supports listing and creation but must not be hard-deleted can omit `"delete"`. The factory then does not register the generic DELETE route for that resource.

This is route construction/configuration, not a runtime permission system. It does **not** replace authentication or user-level authorization.

---

## 6. How the master resources use the generic router

The master API modules are thin configuration/registration modules. Instead of each module implementing all CRUD handlers itself, it imports its spec and the router factory, builds the router, and exposes it to the main application.

The three generic resources are:

### Fish types

- Spec: `app/specs/fish_type.py`
- Model: `app/models/fish_type.py`
- Schema: `app/schemas/fish_type.py`
- API module: `app/api/fish_types.py`
- Database table: `fish_types`
- Search field: `name`
- Sort fields: `id`, `name`, `is_active`
- Duplicate names are rejected through a database constraint and translated into a conflict response.
- Supports list, create, update, activate/deactivate, and generic delete according to the enabled operations.

### Customers

- Model: `app/models/customer.py`
- Schema: `app/schemas/customer.py`
- API module: `app/api/customers.py`
- Spec lives under `app/specs/`.
- The old dedicated customer service module was removed after its generic master-record behavior was replaced by `RecordService`.
- Customer phone numbers are allowed to be shared/duplicated according to the documented business requirements.
- Customer-specific trip behavior remains separate from generic customer-master CRUD.

### Suppliers

- Model: `app/models/supplier.py`
- Schema: `app/schemas/supplier.py`
- API module: `app/api/suppliers.py`
- Spec lives under `app/specs/`.
- The old dedicated supplier service module was removed after the generic engine took over common master-record behavior.
- Supplier phone numbers may be shared/duplicated according to the requirements.

### What the refactor achieved

Before the refactor, each master API/service pair repeated common operations such as listing, creating, updating, duplicate handling, and activation/deactivation.

After the refactor:

- common database behavior is implemented once;
- common HTTP route behavior is implemented once;
- each resource declares its configuration in a spec;
- the resource's API module registers the generated router;
- resource-specific workflows remain custom when they need different business rules.

The factory does not magically infer every business rule. The spec and schemas must accurately declare the resource's fields and supported operations, and custom workflows still require custom code.

---

## 7. Generic CRUD versus custom trip APIs

The trip domain is not just a set of independent records. It contains relationships and operations that affect multiple records, so it continues to use custom API handlers and service logic.

Relevant files include:

- `app/api/trips.py`
- `app/api/trip_customers.py`
- `app/api/trip_customer_requirements.py`
- `app/services/trip.py`
- trip-related ORM models and schemas.

The work completed includes trip APIs and database structures for trip/customer relationships, trip customer requirements, and trip/fish-type associations.

These endpoints were intentionally not forced into the generic record router. Operations such as copying customers from another trip or working with requirements have domain behavior beyond ordinary create/read/update/delete.

### Important distinction

**Generic CRUD** means: "Create, retrieve, update, activate/deactivate, or delete one record using common rules."

**A custom business operation** means: "Perform a specific action that may inspect or modify multiple related records and must preserve business invariants."

The architecture uses the generic engine for the first category and custom services/routers for the second.

---

## 8. Database models and migrations

SQLAlchemy models define the database entities and relationships. Pydantic schemas define the request/response contract. Alembic version files define the schema changes that can be applied to a database.

The project has migration history for:

- fish types;
- customers;
- suppliers;
- trips;
- trip/customer associations;
- trip customer requirements;
- trip/fish-type associations.

The latest reported Alembic head is:

```text
5cf800408ce3 (head)
```

The command used was:

```bash
uv run alembic heads
```

That command verifies the revision graph's head. It does not by itself prove that every target database has been upgraded to that revision.

Ruff changed import ordering and type annotations in the migration files. The user chose to keep those changes. The reported test and Ruff checks passed afterward.

---

## 9. Error-handling design

The generic service and router divide error handling into two layers.

### Service layer

The service understands operation outcomes:

- record absent;
- database constraint conflict;
- update contains no permitted changes.

It raises Python exceptions representing those outcomes.

### Router layer

The router translates those known exceptions into HTTP responses. This prevents the service from depending directly on HTTP-specific behavior and allows the same service logic to be reused.

Common response meanings include:

| HTTP status | Meaning in this API |
|---|---|
| `201 Created` | A new record was created |
| `204 No Content` | A delete operation succeeded without a response body |
| `404 Not Found` | The requested record does not exist |
| `409 Conflict` | A database constraint or duplicate value prevents the operation |
| `422 Unprocessable Entity` | FastAPI/Pydantic request validation rejects invalid input, where applicable |

The precise status for every invalid input depends on which validation layer detects it.

---

## 10. Tests and verification completed

The last reported verification was:

```bash
uv run ruff check
uv run pytest -q
uv run alembic heads
```

Output:

```text
All checks passed!
73 passed in 3.42s
5cf800408ce3 (head)
```

The following also ran without reporting whitespace errors:

```bash
git diff --check
```

Additional behavior confirmed during development:

- The generic router registered one DELETE route for each of fish types, customers, and suppliers.
- The generic fish-type delete endpoint returned `204 No Content` for a successfully deleted record.
- Duplicate-name create/update behavior is covered by tests.
- The suite passed after fixing a test variable accidentally removed during lint cleanup.
- Ruff is installed as a development dependency.
- Ruff's `B008` rule is ignored in `pyproject.toml` because FastAPI dependency injection commonly uses `Depends(...)` in route parameters.

### Why the test fix mattered

A test created a destination trip and used `destination_trip_id` in later requests. During cleanup, the assignment was replaced by an unassigned `create_trip(client)` call. That removed the ID while later test lines still referenced it, causing `NameError` and Ruff `F821` failures.

The assignment was restored in the test that needs the ID. The test suite then returned to 73 passing tests. In the separate test where the ID is unused, the trip creation can remain unassigned if the test still needs the destination trip to exist.

---

## 11. Ruff cleanup

Ruff was added to the development dependencies and run across the project. The cleanup included import sorting/unused-import fixes and type-annotation style updates.

The project configuration contains:

```toml
[tool.ruff.lint]
ignore = ["B008"]
```

This suppresses the `B008` warning for function-call defaults such as FastAPI's `Depends(get_db)`. This is a deliberate framework-specific configuration, not evidence that all lint rules are disabled.

The old master service files were deleted:

- `app/services/customer.py`
- `app/services/fish_type.py`
- `app/services/supplier.py`

A repository search found no remaining Python imports referencing those old service modules at the time of the check.

---

## 12. Git and completion state

The user reported that the latest code and cleanup were working and asked for the completed record. At the last verification, Ruff, tests, Alembic head inspection, and `git diff --check` succeeded.

The project changes included:

- new generic core files;
- new resource specifications;
- refactored master API modules;
- removed old master service modules;
- trip-related APIs/models/schemas/services and migrations;
- Ruff configuration and lockfile updates;
- test cleanup.

**Do not infer that a commit exists from passing tests.** The commit should be confirmed by checking `git log -1 --oneline` and `git status --short` in the local repository. This document records the reported implementation and test state, not a live inspection of the current checkout.

---
## 12A. Trip workflow built on the foundation

### 12A.1 Endpoints (all under /api/trips)
- POST /{trip_id}/supplier-deliveries, GET list, GET one (supplier slips)
- POST /{trip_id}/handovers, GET list, GET one
- GET /{trip_id}/stock
- GET /{trip_id}/handover-totals
- POST /{trip_id}/close

### 12A.2 Supplier slips
A slip records bags actually delivered by the supplier, per fish type, with rejected and damaged counts. A slip can be recorded with or without a finalized supplier list. Several slips per list are allowed (migration 80af31dc8519 dropped the unique constraint; the service guard was removed). A closed trip rejects new slips with 409. The first successful slip moves the trip from PLANNING to IN_PROGRESS in the same transaction.

### 12A.3 Handovers
A handover records bags given to one trip customer, with one or more fish lines. Tables: handovers, handover_lines (migration 25f4df3a2c84).
- Each submit carries a unique submit_reference. Same reference and same data returns the existing handover with 200. Same reference with different data returns 409.
- Zero-bag lines are allowed. Negative bags, empty lines, duplicate fish lines, and blank references return 422.
- Unknown trip, trip customer, or fish type returns 404. Nothing is saved on failure.
- A closed trip returns 409.
- A handover above slip quantity, or for a fish not on any slip, is allowed and flagged, not blocked.

### 12A.4 Stock
left_bags = slip_bags − handed_bags. Rejected and damaged bags are informational and do not change left_bags. over_slip is true when handed_bags exceeds slip_bags. Stock sums all slips for the trip. handover-totals sums bags per trip customer and fish type.

### 12A.5 Trip lifecycle
PLANNING → IN_PROGRESS → CLOSED.
- IN_PROGRESS is set by the first successful slip.
- POST /close requires IN_PROGRESS, otherwise 409. It is rejected with 409 and a message such as "Stock left. Rohu: 10" when any fish type has left_bags above zero. Negative left_bags does not block close.
- A successful close sets status CLOSED and closed_at (migration 660ceb17f3e0), then returns the trip, final stock, and customer totals.
- Slip, handover, and close take a row lock on the trip, so a slip or handover cannot slip in while a close runs.
- Leftover fish is recorded as an ordinary handover to a customer named Self. There is no separate dam or leftover record.

### 12A.6 Tests
tests/test_handover.py covers handovers, stock, idempotency, rollback, and the lifecycle (first slip status, failed slip, close with and without stock left, double close, closed-trip rejections, negative stock).

### 12A.7 Known gaps and differences from the target documents
- Close here is the simple stock gate. REQUIREMENTS.md (Phase 14 and 15) wants both quantity and money reconciliation confirmations, version snapshots, locking, and audit. Not built.
- Status values are PLANNING, IN_PROGRESS, CLOSED, not the DRAFT/PLANNED/DISTRIBUTING/RECONCILING/COMPLETED set in the requirements.
- Handover has no draft state, no selling rate, and no bill (Phase 9 and 10).
- No stock movement ledger. Stock is computed from slips and handovers.
- No authentication yet (Phase 1) and no meeting points (Phase 3).
- No handover reversal or replacement. No confirm gate for over-slip handovers.
- A retry of an old handover after the trip closes returns 409 instead of the original record.
- Trips created before the lifecycle change keep status PLANNING even if they hold slips.

## 13. What is completed versus not yet implemented

This document records the completed foundation; it does not claim the whole fish-distribution product is finished.

### Completed in the reported implementation

- FastAPI/SQLAlchemy/Alembic project foundation.
- Fish type, customer, and supplier master records.
- Shared `RecordSpec` / `RecordService` / `make_record_router` engine.
- Common list, get, create, update, activate/deactivate, and generic delete behavior where enabled.
- Search and allow-listed sorting in the generic list service.
- Generic exception-to-HTTP error translation.
- Trip APIs and trip-related association/requirement structures.
- Ruff cleanup.
- 73 passing tests and a clean reported `git diff --check`.
- Alembic revision head reported as `5cf800408ce3`.

### Not established as completed by this work record

The broader product requirements still include planned work for:

- owner authentication and authorization;
- trip planning details and planned quantities;
- supplier requirement aggregation, independent adjustment, sending, and immutable revisions;
- delivery drafts and explicit actual-delivery confirmation;
- rate snapshots and billing;
- payment ledger, trip allocations, customer dues;
- supplier receiving, returns, defects, and stock reconciliation;
- expenses, supplier settlement, profit/loss reports;
- completed-trip locking, re-authentication to unlock, drafts, versions, and audit history;
- payment gateway integration, backups, recovery drills, and production deployment.

Those are future phases unless separately implemented and verified. Passing the current tests does not imply they already exist.

---

## 14. End-to-end explanation: how a master-data request works

Take a request to create a fish type as an example.

1. A client sends a POST request to the fish-type collection endpoint with JSON containing the fish-type name.
2. FastAPI matches the route that was registered when `make_record_router(...)` built the fish-type router.
3. FastAPI validates the body against the fish-type create schema.
4. The route's `Depends(get_db)` dependency provides a SQLAlchemy session.
5. The route constructs the configured service with the session and `FISH_TYPE` spec.
6. The service builds a `FishType` ORM object from validated input and adds it to the session.
7. The service commits the transaction.
8. If the database rejects the insert because of an integrity constraint, the service rolls back and raises `RecordConflictError`.
9. The router catches that known error and responds with HTTP `409 Conflict`.
10. If the insert succeeds, the service refreshes the object and returns it.
11. FastAPI serializes the returned object according to the read schema and returns HTTP `201 Created`.

For a DELETE request, the same router/service boundary applies, but the service deletes the row and commits. Success returns `204`; missing records return `404`; a foreign-key conflict returns `409`.

The key architectural achievement is that the route and database algorithm do not need to be rewritten for every master resource. The spec supplies the resource-specific configuration, while the generic service and router implement the common mechanism.

---

## 15. Final architecture summary

```text
                     FastAPI application
                             │
              ┌──────────────┴──────────────┐
              │                             │
       Master-data APIs                Custom trip APIs
              │                             │
      make_record_router             Domain-specific routes
              │                             │
       RecordSpec + service           Trip service/logic
              │                             │
              └──────────────┬──────────────┘
                             │
                       SQLAlchemy ORM
                             │
                         PostgreSQL
                             ▲
                             │
                         Alembic
                 manages schema migrations
```

Last reported verification: Ruff passed; 163 tests passed; Alembic reported 660ceb17f3e0 (head).

## 12B. Selling rates and bill

### Rates
Rates are per bag, `Numeric(10,2)`, zero or more.
- Trip default: `trip_fish_types.rate_per_bag`, one per fish type per trip.
- Customer override: table `trip_customer_rates`, one per trip customer and fish type.
- Rates are write-only. `PUT /api/trips/{id}/rates` and
  `PUT /api/trips/{id}/customers/{trip_customer_id}/rates` return only
  `{fish_type_id, rate_set}`. `GET /api/trips/{id}/rate-status` returns
  flags only. No response in the API returns a rate number.
- Setting a rate again overwrites it. A fish must be configured on the trip, else 404.

### Pricing a handover
At submit, each handover line saves a rate: customer override, else trip default,
else null (unpriced). The handover still saves with a null rate.
When a rate is set later, it fills unpriced lines only. For a default, customers
with their own override for that fish are skipped. Priced lines never change.

### Bill
`GET /api/trips/{id}/bill` returns per trip customer: total_bags, unpriced_bags,
total_amount, complete, plus trip totals. Amount = sum of bags x saved line rate,
priced lines only. No per-fish amounts. Amounts are strings with two decimals.
Works on a closed trip. Close is not blocked by unpriced lines.

### Privacy
The UI must never show rates. With one fish type, total divided by bags reveals a
rate, so the bill screen must not sit on a list or home page. Real protection needs
owner authentication (next slice).

### Tests
tests/test_rates.py: set and overwrite rates, validation, overrides, rate-status,
late pricing, saved line rates, no rate fields in responses, bill totals and
incomplete bills.

Last reported verification: Ruff passed; 197 tests passed; Alembic reported e46929cb17c6 (head).

## 12C. Owner authentication

- One owner, created by `python -m app.cli create-owner`. No signup endpoint.
  Password at least 12 characters, stored as Argon2id.
- Sessions live in table `owner_sessions`. Only a SHA-256 hash of the token is
  stored. Cookie is HttpOnly, SameSite and Secure from `.env`.
  Idle limit 8 hours, absolute limit 7 days. A password reset signs out everyone.
- Endpoints: `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me`.
  Bearer header is also accepted. Login returns the token in the body only
  when the client asks for it.
- Every router except health and auth is guarded in `main.py`.
  `tests/test_guard.py` walks the OpenAPI route list and fails on any open route.
- Login lock: 5 failures per IP, 20 per username, 15 minute lock, in memory.
- CORS lists exact origins from `CORS_ORIGINS` and allows credentials.
  Writes from other origins return 403. `/docs` is off when `APP_ENV=production`.
- Tests use fixture `client` (fake owner) and `raw_client` (real login).

### Not done
- 2FA (TOTP). Required before the app goes on the internet.
- Login lock is per process and resets on restart.
- Behind a proxy, the lock sees the proxy IP until trusted proxy headers are set.
- Test PostgreSQL tables come from Alembic. Always open each autogenerated
  migration before applying it. `migrations/env.py` must import every model.

Last reported verification: Ruff passed; 302 tests passed; Alembic reported bee732cfae8b (head).