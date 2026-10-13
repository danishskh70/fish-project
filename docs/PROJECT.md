# PROJECT.md — Fish Distribution Management Application

## 1. Purpose

Build a fast, reliable, owner-operated application for managing fish-seed distribution trips. The application replaces scattered notes, manual calculations, and memory-dependent follow-up with one auditable record of customer plans, supplier requirements, bags received and distributed, money collected, unpaid balances, expenses, and trip results.

The application is not a customer portal, driver app, supplier portal, or multi-tenant SaaS product in its first release. The owner uses it directly during busy distribution operations. Customers, drivers, and suppliers do not log in. The owner communicates with them outside the application.

## 2. Business problem

The owner needs to coordinate three distribution spots, customer quantities, fish types, supplier orders, meeting-point order, delivery quantities, changing selling rates, cash and other payments, returns, defects, and trip costs. Work is time-sensitive and interruptions are common. The system must be fast enough for use while distributing bags, yet strict enough to detect missing bags, missed customer bills, unrecorded payments, and unexplained differences.

The key outcome is not merely storing records. It is helping the owner prove at trip close that:
1. Every bag is accounted for.
2. Every customer delivery has a correctly reviewed bill.
3. Every payment and remaining balance is visible.
4. Every money or quantity discrepancy is highlighted and handled explicitly.
5. Supplier cost and other expenses are included in the final result.
6. Completed records are locked and can only be changed through a controlled, auditable correction process.

## 3. Product principles

- Owner-only operation in the initial release.
- Fast, low-tap workflows with sensible defaults and automatic arithmetic.
- Draft-first for interruptible work; saved drafts survive navigation and restart.
- Explicit separation between planned values, actual values, confirmed payments, and unresolved differences.
- Preserve historical truth: do not silently rewrite sent supplier requirements, locked trip versions, payment history, or audit records.
- Show both detail and totals; never make the owner use an external calculator for ordinary trip calculations.
- A warning identifies a discrepancy; it must not accuse a person or decide who is right.
- Record the owner's decision and explanation where a difference is accepted or resolved.
- Keep trip completion separate from collection of outstanding customer balances.
- Never treat cash collected as equivalent to sales revenue or profit.
- Use a small, understandable architecture that can be extended after real usage.

## 4. Users and access

### Owner
The only application user in the first release. The owner creates and edits master data, plans trips, sends/revises supplier requirements, records receiving, deliveries, payments, returns, defects, expenses, reconciles quantities and money, closes and locks trips, unlocks completed trips with re-authentication and a reason, and reviews reports.

### Future administrator/manager
Not part of the initial release. The owner may later want an administrator identity or manager permissions, but do not implement a manager workflow unless separately approved. Current completed-trip unlocking is owner-only.

### External people
Customers, drivers, and suppliers have no accounts and no direct application access. The owner records information received from them.

## 5. Initial product scope

### Included
- Authentication for one owner identity and protected owner-only APIs.
- Fish Type Master.
- Customer Master, including active/inactive status and default meeting point.
- Supplier Master.
- Trips and trip lifecycle.
- Trip customer selection and planned quantities.
- Reuse customer list from a previous trip without copying previous quantities.
- Customer-specific planned quantities by fish type.
- Aggregated supplier requirement with independent owner-editable quantities and sent revisions.
- Meeting-point grouping and custom ordering.
- Actual supplier receiving, rates, returns, defects, and stock ledger.
- Customer delivery entry, draft persistence, actual quantities, price rules, bills, and adjustments.
- Manual payments and a payment-provider abstraction for a later integrated gateway.
- Customer balances across trips, allocation, settlement decisions, and reminders.
- Trip expenses, supplier settlement, quantity and financial reconciliation.
- Trip completion, locked versions, unlock workflow, drafts, audit trail, and current-version view.
- Reports for customer sales, collections, balances, stock, costs, and profit/loss.
- Automated tests, migrations, backups, and operational documentation.

### Explicitly excluded from the initial release
- Customer, driver, or supplier login.
- Driver-facing application or tracking.
- Automatic supplier communication/acceptance tracking.
- Multiple suppliers per trip; the current business rule is one supplier per trip.
- Payment gateway production integration until a provider is selected. The architecture may support test-mode integration later.
- Automatic assumption that a supplier return creates a credit/refund.
- AI features.
- Multi-tenant hosting, public registration, and manager roles.
- Silent deletion or rewriting of financial or audit history.

## 6. Working assumptions and confirmed rules

- The business distributes fish seed, with quantities commonly expressed in bags.
- There are three distribution spots, represented as configurable meeting points rather than hard-coded application logic.
- One trip has one supplier.
- Owner controls customer inclusion and trip quantities.
- Customer active status is different from inclusion in a particular trip.
- A new trip can start with a manually selected customer list, a selection from all active customers, or the customer list from a previous trip. Previous quantities are not copied automatically.
- Owner may edit planned customers/quantities until the supplier requirement is first sent. After sending, edits create a new requirement revision; previously sent versions remain preserved.
- The system records sent status and timestamp but does not claim that the supplier accepted the order.
- Customer planned quantities are aggregated by fish type to propose supplier quantities; owner can independently change supplier quantities.
- Each customer has a default meeting point. The owner can override a meeting point or order for a particular trip without altering master data or past trips.
- Planned quantities are defaults only. Actual quantities drive the final bill and stock calculations.
- Delivery drafts must not be mistaken for confirmed deliveries.
- The selling rate may change. Preserve the rate used for each bill line and all rate changes.
- Payments are individual transactions, not an overwritten cumulative field.
- Unpaid balances can remain after trip closure and must stay visible.
- Later payments update current payment status in the customer profile and trip financial view without unlocking or rewriting the locked trip.
- Completing a trip requires owner confirmation of both bag and money reconciliation. Documented differences and unpaid balances may remain visible.
- A completed trip is locked by default. Unlock requires owner re-authentication and a reason. Saved corrections create a new version; the previous locked version remains immutable.
- Unfinished corrections are stored as drafts and must not replace the current locked version.
- Owner can mark a small remaining customer amount as waived or no longer pursued, but must choose how it is handled. A configurable cumulative per-customer/per-trip threshold triggers a mandatory reason only when the cumulative adjustment exceeds the threshold.
- Current payment allocation behavior: owner chooses the trip balance; the UI can suggest a default, such as oldest first, but must not force that allocation.

## 7. Technology and implementation context

The existing learning/application repository is `~/projects/fish-project`. It already contains FastAPI, SQLAlchemy, Pydantic, Alembic, PostgreSQL configuration, and master-data APIs for fish types, customers, and suppliers, with tests using in-memory SQLite. Preserve this repository and its migration history. Inspect it before changing anything. Do not replace it with a generated prototype.

Expected stack:
- Python with `uv` for project/dependency management.
- FastAPI for HTTP APIs.
- Pydantic for request/response validation.
- SQLAlchemy for persistence and relationships.
- PostgreSQL for real application data.
- Alembic for schema migrations.
- Pytest for automated tests; SQLite may be used for isolated tests where behavior is compatible, with PostgreSQL integration tests for database-specific behavior.
- Frontend technology is not finalized in this document. Keep backend contracts independent of the UI. Select/confirm the frontend before implementing a production user interface.
- Payment gateway provider is undecided and must be isolated behind an adapter.

## 8. Success criteria

The MVP is successful when the owner can complete a real trip from planning through reconciliation using the application, and:
- No trip quantity is silently copied from a previous trip.
- A supplier requirement sent once remains historically available after revisions.
- Actual delivery quantities and applicable rates determine customer bills.
- Every recorded payment has its own history entry and can be allocated to a specific trip balance.
- Outstanding balances remain visible across trips and update when payment is recorded.
- Received, returned, delivered, defective, and remaining quantities can be reconciled by fish type.
- Money collected, sales, receivables, supplier cost, other expenses, and profit/loss are shown separately.
- The owner cannot complete a trip without confirming both reconciliations.
- Locked trip versions cannot be changed through ordinary edit APIs.
- Unlocking and correction leave a traceable audit history and preserve the prior version.
- Tests cover calculations, permissions, state transitions, concurrency-sensitive writes, and failure cases.

## 9. Development rule

Build one end-to-end vertical slice at a time. First inspect and test the current repository. Reuse and improve existing master-data functionality rather than replacing it. For each slice: state the behavior, identify the smallest change, implement, migrate, test, inspect the diff, and commit. Do not implement unresolved business decisions by guessing; label them as open decisions in `REQUIREMENTS.md`.
