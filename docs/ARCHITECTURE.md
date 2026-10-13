# ARCHITECTURE.md — System Architecture

## 1. Architectural goals

Build a small, explicit FastAPI application that can be understood and tested module by module. The application is owner-operated and transaction-heavy. Correctness, traceability, and safe historical changes matter more than generic abstractions.

Architecture must support:
- Master data and trip workflows.
- Immutable supplier requirement revisions.
- Actual stock movements and reconciliation.
- Customer bills, payment transactions, allocations, and receivables.
- Locked trip snapshots and correction drafts.
- Append-only audit events.
- A future payment gateway without coupling business logic to one provider.

Do not replace the existing `~/projects/fish-project` repository. Inspect the current structure and reuse its `app/api`, `app/models`, `app/schemas`, `app/services`, `app/db`, `app/core`, migrations, and tests patterns.

## 2. Recommended logical layers

### API/router layer
Responsibilities:
- Define HTTP paths, methods, request/response schemas, status codes.
- Resolve authenticated owner and database session.
- Call one service operation.
- Convert known domain errors into consistent HTTP errors.
- Avoid embedding business calculations or multi-step persistence logic.

### Schema layer
Responsibilities:
- Validate request shape and response contracts with Pydantic.
- Distinguish create/update/read schemas.
- Reject fields clients must not control, such as actor identity, locked state, computed totals, and current version.
- Use explicit decimal and quantity constraints.

### Service/domain layer
Responsibilities:
- Enforce business rules and state transitions.
- Perform calculations and orchestrate transactions.
- Enforce lock/unlock rules, allocations, stock movement rules, versioning, and audit events.
- Be testable without HTTP.

### Model/persistence layer
Responsibilities:
- SQLAlchemy tables, relationships, constraints, indexes, and foreign keys.
- Use PostgreSQL as production database.
- Avoid model methods that hide complex workflow side effects.

### Database/session layer
Responsibilities:
- Create engine/session from configuration.
- Use one transaction per atomic service operation.
- Roll back completely on failure.
- Migrations managed by Alembic.

### Frontend (not finalized)
UI should call API contracts and present owner-focused screens. Keep UI choices out of backend business rules. Server is authoritative for totals, permissions, state, and audit. Client may preview arithmetic for speed, but server recomputes and validates it.

## 3. Suggested module layout

Adapt to the existing repository rather than mechanically creating every file immediately.

```text
app/
  api/
    auth.py
    health.py
    fish_types.py
    customers.py
    suppliers.py
    meeting_points.py
    trips.py
    trip_customers.py
    supplier_requirements.py
    receiving.py
    deliveries.py
    payments.py
    customer_balances.py
    returns.py
    defects.py
    expenses.py
    reconciliation.py
    reports.py
    audit.py
  core/
    config.py
    security.py
    errors.py
  db/
    session.py
    base.py
  models/
    user.py
    fish_type.py
    customer.py
    supplier.py
    meeting_point.py
    trip.py
    trip_customer.py
    trip_fish_plan.py
    supplier_requirement_revision.py
    supplier_requirement_line.py
    stock_movement.py
    receiving_line.py
    supplier_return.py
    defect_record.py
    delivery.py
    delivery_line.py
    bill_adjustment.py
    payment.py
    payment_allocation.py
    settlement_adjustment.py
    supplier_payment.py
    supplier_credit.py
    trip_expense.py
    reconciliation.py
    trip_version.py
    correction_draft.py
    audit_event.py
  schemas/
  services/
  repositories/  # optional; add only if query complexity justifies it
migrations/
tests/
  unit/
  api/
  integration/
```

This is a target shape, not a requirement to create empty modules all at once. Existing master files remain in place and can be extended gradually.

## 4. Core domain model and relationships

### Identity and master data
- `User`: owner login, password hash, active flag, security timestamps.
- `FishType`: name, active flag, created/updated timestamps.
- `Customer`: display name, contact details, active flag, default meeting point reference.
- `Supplier`: name/contact/active flag.
- `MeetingPoint`: name, active flag, optional display/order metadata.

Master records should generally be deactivated rather than deleted when referenced by transactions.

### Trip and plan
- `Trip`: date, one supplier, lifecycle state, current version number, locked status, created/updated metadata.
- `TripCustomer`: trip/customer link, inclusion, meeting-point snapshot/override, ordering fields.
- `TripPlannedLine` or equivalent: trip/customer/fish type, planned quantity. Store quantities for the new trip independently of source trip.
- Trip-level selling-rate defaults per fish type.
- Customer-specific trip rate overrides per fish type.

A customer master default and trip-specific values are distinct. A trip's order or meeting-point override cannot mutate a customer's default.

### Supplier requirement revisions
- `SupplierRequirementRevision`: trip, revision number, status/draft/sent, sent timestamp, actor, snapshot metadata.
- `SupplierRequirementLine`: revision, fish type, suggested quantity, requested quantity, optional notes/rate if required.
- Sent revisions are immutable. A later change produces a new revision. Use database constraints to ensure revision number uniqueness per trip.

### Receiving and stock
- `ReceivingLine`: trip, fish type, actual quantity received, agreed supplier rate, time, notes.
- `StockMovement`: canonical movement ledger entry with trip, fish type, movement type, signed/typed quantity, source record, timestamp, actor.
- `SupplierReturn`: return metadata, fish type quantities, handling method, expected credit.
- `SupplierCredit`: actual confirmed credit/refund, amount, confirmation timestamp, notes.
- `DefectRecord`: trip, fish type, quantity, category/location, optional customer delivery link, status and notes.
- `DriverReportLine`: trip, fish type, driver-reported quantity and source time, entered by owner, notes.
- Avoid storing the same movement twice as separate authoritative totals. Either create the movement ledger from source events in the same transaction or make source lines the canonical ledger and compute balances consistently.

### Delivery and billing
- `Delivery`: trip/customer, status (draft/confirmed), confirmation time, creator, optional notes.
- `DeliveryLine`: delivery, fish type, planned quantity snapshot, actual quantity, applied selling rate, computed line amount or safely recomputable amount.
- `BillAdjustment`: delivery/trip, amount, category/reason, actor/time; cannot silently alter a line price.
- A delivery draft is excluded from confirmed stock and sales totals.
- Applied rate and quantity are snapshotted on confirmed bill lines. A later default rate change must not rewrite past confirmed bill lines.

### Payments and receivables
- `Payment`: customer, amount, currency, method, status, received/confirmed timestamp, external reference if any, note, actor.
- `PaymentAllocation`: payment, trip/customer receivable, allocated amount. One payment may be allocated to multiple trip balances only if owner explicitly chooses a split.
- `SettlementAdjustment`: customer/trip, amount, category (waived/discount or no-longer-pursued), reason, actor/time.
- Balance is derived from bill/adjustment/payment allocation records, not an independently overwritten `paid_amount`.
- Enforce allocation sum <= confirmed payment amount. Excess is held as unallocated customer credit or explicitly handled by the selected overpayment policy.

### Supplier settlement and expenses
- `SupplierPayment`: trip/supplier, amount, method/date/reference.
- `SupplierCredit`: confirmed supplier refund/credit, distinct from expected credit.
- `TripExpense`: trip, category, amount, date, note, actor.
- Supplier payable is calculated from confirmed received quantities/rates and valid adjustments according to agreed supplier-cost policy, less payments/confirmed credits.

### Reconciliation, versions, and audit
- `Reconciliation`: trip, type (quantity/money), status, confirmation actor/time, snapshot of totals and discrepancy items, notes.
- `TripVersion`: trip, version number, immutable snapshot/payload or normalized version reference, created actor/time, lock timestamp, reconciliation references, change summary.
- `CorrectionDraft`: trip, base locked version, mutable working data or staged edits, owner, reason for unlock, created/updated timestamps, optimistic revision.
- `AuditEvent`: append-only event with actor, action, entity type/id, trip/version, timestamp, reason, before/after diff, correlation/request id.
- Payment events after a trip is locked are separate ledger events. Current financial display can derive updated balances without rewriting the old locked snapshot. Clearly distinguish “trip version snapshot at lock time” from “current payment ledger/balance.”

## 5. Critical modeling distinction: operational version vs live ledger

A completed trip has a locked operational snapshot: planned/actual quantities, applied rates, supplier requirement revision, stock records, reconciled state, and financial figures as known at lock time. Later payment collection changes the live payment ledger and outstanding balance. It does not alter the locked bill or silently rewrite the old snapshot.

When the UI opens a trip, show:
- `Vn — Current`
- `Locked` or `Correction draft in progress`
- Snapshot financial state at lock time if useful
- Current live payments and outstanding balances
- Clear timestamps and links to audit/payment history

If a trip correction is saved, create a new current version after re-reconciliation and lock. Previous versions remain viewable. Avoid pretending a later payment created a new trip version unless product behavior is explicitly changed.

## 6. State and transaction design

### Trip states
Use a domain state machine. Suggested states:
`DRAFT → PLANNED → DISTRIBUTING → RECONCILING → COMPLETED/LOCKED`

A completed trip can enter a separate correction workspace only after owner re-authentication and reason. The current locked version remains the baseline while the correction draft exists. Saving/finalizing the correction produces the next version after required validation and reconciliation. A correction draft does not make the baseline mutable.

### Delivery states
`DRAFT → CONFIRMED`
A confirmed delivery may be corrected only under the authorized correction workflow for locked trips. Drafts do not generate confirmed stock movements or sales.

### Payment states
Manual payment: recorded/confirmed by owner. Gateway payment: pending until server-side provider verification; failed/cancelled/unverified statuses do not reduce receivable. Corrections use reversal entries rather than deletion.

### Atomic transactions
The following should be atomic:
- Confirm delivery + its stock movement/bill lines.
- Record payment + allocation + audit event.
- Confirm supplier return + stock movement + expected-credit record.
- Confirm actual supplier credit.
- Finalize reconciliation + create trip version + lock trip.
- Save a finalized correction version + audit diff + lock transition.

Use `session.begin()` or equivalent transaction boundaries. On any failure, all related writes roll back.

## 7. API conventions

Use versioned or consistently namespaced API paths under `/api`. Existing paths should be preserved unless a deliberate migration is planned.

Representative endpoints (illustrative; finalize names with implementation):
- `POST /api/auth/login`
- `GET/POST /api/fish-types`, `PATCH /api/fish-types/{id}`
- `GET/POST /api/customers`, `PATCH /api/customers/{id}`
- `GET/POST /api/suppliers`, `PATCH /api/suppliers/{id}`
- `GET/POST /api/meeting-points`
- `GET/POST /api/trips`
- `GET /api/trips/{id}` — current view with version/lock status and live balance summary
- `POST /api/trips/{id}/customers`
- `PUT /api/trips/{id}/plan`
- `POST /api/trips/{id}/supplier-requirements/revisions`
- `POST /api/trips/{id}/supplier-requirements/{revision}/mark-sent`
- `POST /api/trips/{id}/receiving`
- `POST /api/trips/{id}/deliveries`
- `PATCH /api/deliveries/{id}` — draft only, subject to state/lock rules
- `POST /api/deliveries/{id}/confirm`
- `POST /api/customers/{id}/payments`
- `POST /api/payments/{id}/allocations`
- `POST /api/trips/{id}/returns`
- `POST /api/trips/{id}/expenses`
- `POST /api/trips/{id}/reconciliation/quantity/confirm`
- `POST /api/trips/{id}/reconciliation/money/confirm`
- `POST /api/trips/{id}/complete`
- `POST /api/trips/{id}/unlock`
- `GET /api/trips/{id}/versions`
- `GET /api/trips/{id}/audit`
- `GET /api/customers/{id}/balances`
- `GET /api/trips/{id}/report`

API actions should be explicit for consequential transitions. Do not let generic PATCH update `status=locked`, `current_version`, `owner_id`, computed balances, or audit data.

## 8. Validation and concurrency

- Use decimal arithmetic for money and rates; use database numeric columns.
- Validate quantity is non-negative; apply positive-only rules where a movement must actually move stock.
- Validate all IDs belong to the correct trip/customer/supplier relationship.
- A payment allocation cannot exceed the payment's remaining allocatable amount.
- A trip customer delivery must reference a customer included in that trip, unless owner explicitly adds them first.
- Do not confirm deliveries with incomplete lines or invalid rates.
- Do not close without both reconciliation confirmations.
- Do not allow normal writes against locked trip state.
- Use optimistic locking/revision numbers on correction drafts to prevent stale writes.
- Add uniqueness constraints for trip/version number, trip/supplier-revision number, and idempotency keys where used.
- Use PostgreSQL transactions and constraints for critical invariants; do not rely only on front-end validation.

## 9. Security and audit

- Never store plaintext password or secrets in repository.
- Keep configuration in environment variables or a local ignored env file.
- All business actions use authenticated owner identity.
- Audit sensitive actions with structured before/after diffs.
- Audit entries are append-only in application behavior. Do not expose update/delete endpoints.
- Unlock event must include reason and re-authentication result, without recording the password.
- Payment reversal is a compensating event, not deletion.
- Do not log payment secrets, JWTs, passwords, or gateway credentials.
- Production deployment must use HTTPS and a backup plan.

## 10. Testing strategy

- Unit tests: calculations, settlement threshold, state machine, stock ledger, payment allocation.
- API tests: auth, validation, response shape, authorization, invalid transitions.
- Database integration tests: PostgreSQL constraints, transactions, migrations, decimal arithmetic, concurrent writes.
- Audit tests: previous version preserved, diff recorded, no normal audit mutation.
- Workflow tests: plan → requirement send/revision → receiving → deliveries → payments → reconciliation → lock → later payment → correction draft → new version.
- Failure tests: rollback on error, duplicate submit, invalid payment, stale draft, unauthorized unlock.
- Existing SQLite tests can remain for quick feedback, but PostgreSQL integration tests should validate production-critical behavior.

## 11. Deployment and operations

- Use environment-based configuration.
- Use Alembic migrations as the only normal schema evolution path.
- Provide backup and restore instructions; test restore.
- Add structured logs and health endpoint.
- Use database connection management and production process configuration.
- Keep payment gateway secrets out of source control.
- Frontend/deployment platform remains an open decision; architecture must not assume it.
