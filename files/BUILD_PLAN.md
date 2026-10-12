# BUILD_PLAN.md — Incremental Implementation Plan

## 1. Purpose and rules

This plan builds the application in small end-to-end slices without replacing the existing repository. Every phase must end with working behavior and tests. Do not create a large number of empty modules in advance.

Repository: `~/projects/fish-project`

Known current context:
- FastAPI, SQLAlchemy, Pydantic, Alembic, PostgreSQL configuration.
- Existing fish type, customer, and supplier master APIs.
- Existing tests use in-memory SQLite.
- Supplier Master migration was created and user indicated it was committed. Verify actual repository state with Git before assuming a commit hash or migration head.
- Do not delete or regenerate migrations.
- Do not replace current project with the earlier prototype.

For every slice:
1. Restate the behavior being built.
2. Inspect current code and `git status`.
3. Decide the smallest change.
4. Implement model/schema/service/router as appropriate.
5. Generate and inspect an Alembic migration if schema changes.
6. Add/update tests.
7. Run focused tests, then full test suite.
8. Run `uv run python -m compileall -q app tests main.py` and `git diff --check`.
9. Inspect `git diff`, confirm no secrets or unrelated files.
10. Commit only after tests pass and user approves/normal workflow permits.

## 2. Phase 0 — Baseline and protect existing work

### Tasks
- Inspect `git status --short`, recent `git log`, `alembic heads`, and migration directory.
- Run existing tests.
- Confirm database URL is not accidentally pointed at production for tests.
- Document current endpoints/models and migration head.
- Verify PostgreSQL connection separately from tests.
- Confirm how auth/configuration is currently structured.
- Add no new domain features in this phase.

### Exit criteria
- Clean, understood baseline.
- Existing tests pass or known failures documented.
- Current migration history preserved.
- No working tree changes discarded.

## 3. Phase 1 — Owner authentication and configuration

### Scope
- Owner identity and secure password hash.
- Login, session/token expiration, authenticated dependency.
- Protect all business APIs.
- Owner actor derived from authentication, never from client-supplied ID.
- Re-authentication primitive for sensitive actions.

### Tests
- Login success/failure.
- Unauthenticated business API rejected.
- Invalid/expired credentials rejected.
- Password not stored or returned as plaintext.
- Owner ID cannot be forged by request body.

### Exit criteria
All protected APIs consistently require owner authentication. Avoid building full UI until API auth contract is stable.

## 4. Phase 2 — Stabilize master data

### Scope
Review and complete existing:
- Fish Type Master.
- Customer Master.
- Supplier Master.

Add only confirmed gaps:
- Active/inactive behavior.
- Stable IDs and historical references.
- Customer default meeting point field when meeting-point module is ready.
- Search/filter useful for fast operations.
- Safe deactivation and duplicate-name validation.
- Avoid phone uniqueness for customers/suppliers.

### Tests
Create/list/update/deactivate; duplicates; inactive records in historical references; no destructive deletion.

### Exit criteria
Master data APIs remain tested and stable. Existing migrations stay intact.

## 5. Phase 3 — Meeting points

### Scope
- Configurable meeting points.
- Customer default meeting point.
- Active status and ordering metadata.
- No hard-coded three-point limit.

### Tests
Create/list/deactivate point; assign customer default; historical trip override later does not mutate default.

### Exit criteria
Master data can express the current three spots and future changes.

## 6. Phase 4 — Trip shell and lifecycle

### Scope
- Trip create/list/detail.
- One supplier per trip.
- Initial draft/planning status.
- Valid state transitions.
- Owner-only access.
- Date/time and current status.

### Tests
Create trip; invalid supplier; no multiple supplier; invalid transition; authentication; trip list/detail.

### Exit criteria
A trip can be created and retrieved, but no customer plan yet.

## 7. Phase 5 — Trip customer selection and planned quantities

### Scope
- Add/remove customers from a trip before supplier requirement send.
- Select from active customers.
- Manually add customers.
- Start from previous trip customer list only.
- Fresh planned quantities required for the new trip.
- Planned quantity per customer/fish type.
- Trip-specific meeting-point and customer-order overrides.
- Persist drafts.

### Tests
Previous quantities are not copied; customer omitted from previous trip can be added; inactive/customer inclusion rules; plan aggregation inputs; reorder does not mutate master defaults.

### Exit criteria
Owner can prepare a fresh trip plan with customers and quantities.

## 8. Phase 6 — Supplier requirement aggregation and revisions

### Scope
- Aggregate planned quantities by fish type.
- Owner can override supplier quantity.
- Display plan total vs requested total and difference.
- Draft requirement revision.
- Mark revision sent with actor/timestamp.
- Once sent, immutable snapshot.
- Further edits create a new revision.

### Tests
Aggregation correctness; independent override; send snapshot immutable; new revision preserves old; supplier acceptance not fabricated.

### Exit criteria
Owner can create, review, mark sent, and revise a supplier request.

## 9. Phase 7 — Actual supplier receiving and stock ledger

### Scope
- Actual quantity received per fish type.
- Agreed supplier rate.
- Variance against requested quantity.
- Canonical stock movement model or equivalent consistent ledger.
- Basic expected remaining calculation.

### Tests
Over/under-delivery; negative quantity rejection; transaction rollback; no double count.

### Exit criteria
Actual receipt is recorded independently of requested quantity.

## 10. Phase 8 — Returns, defects, driver reports

### Scope
- Record supplier returns and handling method.
- Calculate expected credit but require owner confirmation of actual credit/refund.
- Defects before distribution, optional customer-related defects, and end-of-trip defects.
- Aggregate defect entry and optional detailed entries without double-counting.
- Record driver-reported quantities separately.
- Compare owner totals, driver report, and physical count.
- Add discrepancy explanation/resolution while preserving original inputs.

### Tests
Return changes stock exactly once; expected credit is not treated as actual; defects not double-counted; mismatches remain visible after resolution.

### Exit criteria
Stock exceptions can be recorded and explained without blaming or overwriting source data.

## 11. Phase 9 — Delivery draft and confirmation

### Scope
- Distribution list ordered by meeting point and customer.
- Customer delivery screen.
- Planned quantities as defaults.
- Actual quantity can differ.
- Draft auto-save and resume.
- Confirmed delivery uses actual quantities.
- Delivery lines preserve applied rate.
- Draft excluded from stock and sales.
- Minimal interactions and live totals.

### Tests
Draft persistence; draft excluded from totals; confirmation creates one canonical stock movement; duplicate confirmation blocked; actual quantity drives totals.

### Exit criteria
Owner can record customer deliveries during a trip without losing interrupted work.

## 12. Phase 10 — Selling rates and billing

### Scope
- Trip default selling rate by fish type.
- Customer-specific rate override.
- Applied rate snapshot per confirmed delivery line.
- Line totals, bill totals, explicit adjustments and reasons.
- Rate-change review display.

### Tests
Decimal math; override; rate changes don't rewrite past confirmed bills; negative/invalid rate handling; adjustment audit.

### Exit criteria
Every confirmed customer delivery has a traceable bill based on actual quantities and applied rates.

## 13. Phase 11 — Customer payment ledger and allocations

### Scope
- Manual cash/external UPI/bank payment record.
- Individual payment history.
- Payment allocation to one or more trip balances, owner chooses.
- UI default may suggest oldest first but does not force it.
- Partial payment; outstanding balance.
- Customer profile with trip dates, original bill, allocated payments, adjustments, balance.
- Payment from customer profile without unlocking old trip.
- Overpayment handling selected before shipping this phase.
- Payment reversal as compensating entry.

### Tests
Partial payment; correct trip allocation; prior trip balance update; locked bill unchanged; duplicate submission; overpayment; reversal; allocation never exceeds payment.

### Exit criteria
Customer balances across trips are reliable and visible.

## 14. Phase 12 — Settlement adjustments and reminders

### Scope
- Owner can leave amount outstanding, waive/discount, or mark no-longer-pursued.
- Preserve bill/payment arithmetic.
- Configurable cumulative adjustment threshold per customer per trip.
- Require reason only when cumulative total exceeds threshold.
- Show unpaid balances when opening trip and customer profile.
- Do not count old debt as new sales.

### Tests
Threshold at/below/above; several adjustments cumulatively cross threshold; reason required at crossing; trip-specific balance flags; old debt persists.

### Exit criteria
Owner can handle unpaid debt without forgetting or erasing its history.

## 15. Phase 13 — Supplier settlement and trip expenses

### Scope
- Supplier payable/cost.
- Supplier payments and partial payments.
- Expected vs confirmed supplier credits/refunds.
- Other trip expenses.
- Keep supplier requirements and receipt as supporting detail in reports.

### Tests
Payment and credit arithmetic; confirmed credit only; expense totals; supplier balance.

### Exit criteria
Trip financial inputs are complete enough for transparent reporting.

## 16. Phase 14 — Reconciliation

### Scope
- Bag reconciliation by fish type.
- Money reconciliation.
- Review rates and overrides.
- Review supplier settlement and customer outstanding balances.
- Record driver-reported values, physical count, explanations, unresolved differences.
- Checklist requiring both quantity and money confirmations.
- Allow documented differences and unpaid balances.

### Tests
Cannot complete without both confirmations; unresolved difference must be documented; unpaid balances don't block close; discrepancy resolution doesn't erase source values.

### Exit criteria
Owner can see and confirm whether every bag and expected amount has been accounted for.

## 17. Phase 15 — Trip locking, correction drafts, versions, audit

### Scope
- Completing trip creates version V1 and locks it.
- View mode identifies current version and lock state.
- Ordinary updates to locked trip rejected.
- Owner re-authentication and reason to unlock.
- Correction draft separate from locked baseline.
- Draft auto-save and resume.
- Finalized correction creates next version only after review/reconciliation.
- Preserve previous versions and before/after audit.
- Re-lock after reconciliation.
- Later payments update live balances but do not create an operational correction version.
- Audit events append-only through application behavior.

### Tests
Locked mutation blocked; unlock auth/reason; draft survives; abandoned draft leaves baseline unchanged; save creates next version; previous version immutable; audit diff complete; later payment doesn't rewrite snapshot; relock requires reconciliation.

### Exit criteria
Strict, understandable historical correction behavior works end to end.

## 18. Phase 16 — Reports and dashboard

### Scope
- Home dashboard: current trips, outstanding money, unresolved discrepancies.
- Customer-centric trip report.
- Sales vs collections vs receivables.
- Stock received/returned/delivered/defective/remaining.
- Supplier cost/payment/credit, other expenses.
- Provisional or finalized trip result with clear inventory accounting assumptions.
- Customer profile payment and debt history.
- Version history and audit viewer.

### Tests
Totals reconcile with source records; no double counting; current balances reflect later payments; report snapshot and live ledger clearly distinguished.

### Exit criteria
Owner can answer: how much sold, how much received, who owes what, where bags went, what costs were incurred, and what result the trip produced.

## 19. Phase 17 — Payment gateway adapter (after provider decision)

### Scope
- Select provider and document onboarding/fees.
- Test-mode payment link/QR.
- Create pending payment intent.
- Verify status server-side using provider API/webhook and signature validation.
- Idempotent webhook processing.
- Pending/failed/unverified payments never reduce balances.
- Reconcile provider events with local payment records.

### Exit criteria
No payment is considered received based only on a client-side success screen.

## 20. Phase 18 — Hardening and release

### Tasks
- PostgreSQL integration suite.
- Backup and restore test.
- Migration upgrade test from current schema.
- Security review of auth, owner-only actions, secrets, logs, and audit paths.
- Error handling and duplicate-submit protection.
- Responsive/fast owner workflow usability test on the actual device.
- Export requirements implemented.
- Deployment instructions and environment configuration.
- Seed/configuration procedure for owner account and meeting points.
- Test complete trip and post-trip payment workflows end to end.

### Release gate
Do not call the app production-ready until critical workflows, backup/restore, auth, locked-version behavior, and payment/stock reconciliation tests pass.

## 21. Recommended first implementation slice

After baseline inspection, build **Trip Shell** only:
1. Trip model/migration.
2. Create/list/detail API.
3. Select exactly one supplier and trip date.
4. Owner-only authorization.
5. Valid initial state and status tests.
6. Verify existing master APIs and all tests remain green.

Do not begin payment gateway, audit versioning, or the entire UI before the trip domain exists. This slice creates the base that subsequent features can use.
