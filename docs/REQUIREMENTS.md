# REQUIREMENTS.md — Software Requirements Specification (SRS)

**Product:** Fish Distribution Management Application  
**Status:** Initial build specification; open decisions are explicitly listed in the final section.  
**Primary user:** Owner only.  
**Purpose:** Provide enough business and system detail to build a useful first production-oriented version without pretending every future requirement is known.

## 1. Introduction

### 1.1 Purpose
This SRS defines the behavior, rules, validations, workflows, and acceptance criteria for an owner-operated fish distribution application. It is the authoritative source for what the first release should do. Architecture and sequencing live in `ARCHITECTURE.md` and `BUILD_PLAN.md`.

### 1.2 Product scope
The system supports planning trips, calculating supplier requirements, organizing distribution, recording actual stock movements, billing customers, recording payments, tracking debt across trips, reconciling bags and money, recording expenses, calculating business results, and preserving strict history when completed trips are corrected.

The system does not provide external logins. The owner enters information obtained from customers, drivers, and suppliers outside the app.

### 1.3 Terms
- **Trip:** One distribution operation with its plan, supplier requirement, receiving, customer deliveries, payments, stock movements, expenses, reconciliation, and close.
- **Planned quantity:** Quantity the owner intends to deliver to a customer.
- **Actual quantity:** Quantity the owner confirms was delivered.
- **Supplier requirement:** Requested quantities sent to the one supplier assigned to the trip.
- **Requirement revision:** Immutable snapshot of the supplier quantities and rates/notes at the time the owner marks that revision sent.
- **Delivery draft:** Persisted work in progress that is not yet a confirmed delivery.
- **Receivable/outstanding balance:** Customer amount still owed after payments and explicitly recorded adjustments.
- **Settlement adjustment:** Amount waived or no longer pursued, with a recorded category and required reason when threshold rules apply.
- **Reconciliation:** Owner review comparing recorded quantities and money against expected/physical/reported totals.
- **Locked version:** Immutable snapshot of a completed trip's operational and financial state at a particular version number.
- **Current version:** The latest saved, finalized trip version. It is labelled clearly in view mode.
- **Draft correction:** Work on an unlocked trip that has not yet been saved as a new finalized version.
- **Audit event:** Append-only record of a significant action, including actor, time, target, before/after information, and reason where applicable.

## 2. Business objectives

1. Reduce forgotten customer quantities, bills, payments, and prior-trip balances.
2. Help the owner avoid missing bags during distribution and closing.
3. Calculate totals automatically and rapidly.
4. Preserve the history of supplier requests, rates, payments, corrections, and settlements.
5. Distinguish sales from collections and profit.
6. Allow normal collection of old debts without unlocking a completed trip.
7. Make it difficult to alter a completed trip without a trace.
8. Keep the interface fast enough for use during a busy trip.

## 3. Actors and permissions

### 3.1 Owner
The only authenticated user in the first release. The owner may perform all operational actions. Sensitive actions—especially unlocking a completed trip—require re-authentication and a reason.

### 3.2 No external actors with application access
Customers, suppliers, drivers, and managers do not sign in. The owner records their statements, delivered quantities, payments, and reports.

### 3.3 Authorization requirements
- All business APIs require owner authentication, except deliberately public health/status endpoints.
- Never trust an owner ID supplied by the client. Derive actor identity from the authenticated session/token.
- The client cannot change a trip's lock state by sending an ordinary update.
- Unlocking requires owner authentication to be re-confirmed (password or equivalent secure re-authentication), plus a non-empty reason.
- Authorization is enforced on the server, not only by hiding UI controls.
- Future roles must be introduced explicitly with a permission matrix; do not assume managers can unlock trips.

## 4. Core business workflow — start to finish

1. Maintain fish types, customers, suppliers, and meeting-point defaults.
2. Create a trip and choose one supplier.
3. Select customers manually, from active customers, or from a previous trip's customer list. Do not copy previous trip quantities.
4. Enter fresh planned quantities for each selected customer and fish type.
5. Review the generated supplier requirement; independently adjust supplier quantities where needed.
6. Mark a requirement revision as sent. Preserve its snapshot and timestamp.
7. Prepare the distribution order by meeting-point group and customer order.
8. Record actual supplier receiving and agreed supplier rates.
9. Record defects, returns, and other stock movements without double-counting.
10. During distribution, open a customer, use planned quantities as defaults, enter actual quantities, review applicable selling rates, and save draft/confirm delivery.
11. Record payment at the same time as delivery or separately. Payments can also be recorded later from the customer profile without unlocking an old trip.
12. Record expenses and supplier payment/credits.
13. Reconcile stock by fish type and investigate discrepancies.
14. Reconcile expected customer charges against payments and outstanding balances; review rate changes and exceptions.
15. Confirm both quantity and money reconciliation; record unresolved differences and notes.
16. Complete and lock the trip, creating a version snapshot.
17. Later, collect old customer balances from the customer profile. Current financial status updates without rewriting the original locked version.
18. If a historical operational value must be corrected, owner re-authenticates, unlocks with reason, edits a persisted draft, saves a new version, re-reconciles, and relocks.

## 5. Functional requirements

Requirement IDs are stable references for implementation and tests.

### 5.1 Authentication and owner session

**FR-AUTH-01 — Owner login:** Provide a secure login for the owner. Do not allow public registration.
**FR-AUTH-02 — Password storage:** Store only a strong password hash, never plaintext. Use a modern password-hashing library and appropriate parameters.
**FR-AUTH-03 — Protected endpoints:** Require authentication for all business data and write operations.
**FR-AUTH-04 — Actor attribution:** Record the authenticated owner as actor for sensitive actions and audit entries.
**FR-AUTH-05 — Re-authentication:** Require fresh password confirmation or an equivalent re-authentication step before unlocking a completed trip.
**FR-AUTH-06 — Session security:** Use secure token/session handling, expiration, and safe secret configuration. Do not hard-code production secrets.
**Acceptance:** Unauthenticated requests cannot read or mutate protected records; a client cannot impersonate a different owner by changing a request field.

### 5.2 Fish Type Master

**FR-FISH-01 — Create fish type:** Owner can create a fish type with a name and any approved operational attributes.
**FR-FISH-02 — List/search:** Owner can find active and inactive fish types.
**FR-FISH-03 — Update:** Owner can edit master information while preserving references from historical transactions.
**FR-FISH-04 — Deactivate:** Owner can deactivate a fish type rather than deleting a type used by historical records.
**FR-FISH-05 — Duplicate names:** Reject duplicate normalized names, with case/whitespace normalization defined consistently.
**FR-FISH-06 — Historical label:** Transaction records must retain a stable fish-type reference and enough historical display information that renaming a master record does not make old reports ambiguous.
**Acceptance:** Deactivated types cannot be selected for new plans unless explicitly allowed, but remain visible in past trips.

### 5.3 Customer Master

**FR-CUST-01 — Create customer:** Store the customer information required for operational identification and contact.
**FR-CUST-02 — List/search/filter:** Find customers by name/contact and filter active/inactive.
**FR-CUST-03 — Update:** Edit profile information without rewriting historical trip snapshots.
**FR-CUST-04 — Active status:** Active/inactive status indicates whether the customer is currently used in the business. It does not determine whether the customer is included in a particular trip.
**FR-CUST-05 — Default meeting point:** Store a customer's default meeting point.
**FR-CUST-06 — Duplicate phone:** Phone numbers are not required to be unique; family members or multiple customers may share a number.
**FR-CUST-07 — Historical profile:** Customer profile displays trip history, deliveries, bills, payment history, and outstanding amounts by trip.
**FR-CUST-08 — Debt summary:** Show the total outstanding balance and a per-trip breakdown with trip date, original bill, payments allocated, adjustments, and remaining balance.
**FR-CUST-09 — Deactivate, don't erase:** Deactivation must not remove outstanding debt or historical activity.
**Acceptance:** A customer may be active but excluded from a trip; a customer with old debt remains visible even if inactive.

### 5.4 Supplier Master

**FR-SUP-01 — Create/list/search/update supplier:** Owner manages supplier contact details and active status.
**FR-SUP-02 — Deactivate:** Preserve supplier links in old trips and supplier settlements.
**FR-SUP-03 — Phone uniqueness:** Do not require unique supplier phone numbers.
**FR-SUP-04 — One supplier per trip:** A trip has exactly one selected supplier under current business rules.
**Acceptance:** Old trips remain readable after supplier master data is updated or deactivated.

### 5.5 Meeting points and ordering

**FR-POINT-01 — Defaults:** Customer profile can contain a default meeting point.
**FR-POINT-02 — Grouping:** The trip plan groups selected customers by meeting point.
**FR-POINT-03 — Group order:** Owner can reorder meeting-point groups.
**FR-POINT-04 — Customer order:** Owner can reorder customers inside a group or use a fully custom trip order.
**FR-POINT-05 — Trip override:** Owner can override a meeting point or order for one trip without changing the customer default or past trips.
**FR-POINT-06 — Configurable spots:** The business currently has three distribution spots, but they must be configurable rather than hard-coded.
**Acceptance:** Reordering one trip does not alter another trip or the customer default.

### 5.6 Trip planning and customer selection

**FR-TRIP-01 — Create trip:** Owner creates a trip with its date/time and one supplier. Additional trip fields may be introduced when approved.
**FR-TRIP-02 — Customer selection modes:** Support (a) manual add, (b) selecting from active customers, and (c) starting with the customer list from a previous trip.
**FR-TRIP-03 — Copy list only:** When copying from a previous trip, copy only the customer selection/list and optionally reusable order/meeting-point arrangement if owner explicitly chooses it; do not copy previous planned quantities.
**FR-TRIP-04 — Fresh quantities:** Require fresh planned quantities for the new trip.
**FR-TRIP-05 — Add missed customer:** Owner can add a customer not included in the source/previous trip.
**FR-TRIP-06 — Active vs included:** A customer's active status does not automatically include them in a trip.
**FR-TRIP-07 — Edit plan before send:** Owner can edit customer selection and planned quantities until the first supplier requirement is sent.
**FR-TRIP-08 — Trip status:** Trip status must represent its lifecycle (for example, draft/planning, planned, distributing, reconciling, completed/locked). Exact labels may be finalized during implementation, but invalid transitions must be blocked.
**FR-TRIP-09 — Draft persistence:** Planning changes persist as drafts and survive navigation/restart.
**FR-TRIP-10 — No silent copy:** UI must visibly indicate quantities are new/blank when a customer list is reused.
**Acceptance:** Starting from a prior trip does not accidentally reuse the old quantities or bills.

### 5.7 Supplier requirement and revisions

**FR-REQ-01 — Automatic aggregation:** Calculate suggested supplier quantity by fish type by summing planned quantities for all included customers.
**FR-REQ-02 — Independent override:** Owner may adjust the supplier quantity independently of the customer-plan aggregate.
**FR-REQ-03 — Difference visibility:** Show system-calculated customer-plan total, owner-requested supplier quantity, and difference per fish type.
**FR-REQ-04 — Send marker:** Owner can mark a requirement revision as sent and record timestamp and actor.
**FR-REQ-05 — No acceptance assumption:** Do not claim supplier accepted/confirmed; only track that owner marked the requirement sent.
**FR-REQ-06 — Immutable sent revision:** Preserve quantities and details of each sent revision.
**FR-REQ-07 — Later edits:** After first send, changes create a new revision rather than overwriting the sent one.
**FR-REQ-08 — Resend:** Owner may send a revised requirement for last-minute changes, including supplier availability changes.
**FR-REQ-09 — One supplier:** Requirement belongs to the trip's one supplier.
**Acceptance:** Viewing an earlier sent revision shows the exact quantities that were marked sent at that time.

### 5.8 Supplier receiving, rates, returns, and stock

**FR-STOCK-01 — Actual receipt:** Record actual quantities received by fish type, not just the requested quantities.
**FR-STOCK-02 — Variance:** Compare requested and received quantities and highlight over/under-delivery.
**FR-STOCK-03 — Supplier rate:** Record agreed supplier rate by fish type/quantity unit for the trip, with historical preservation.
**FR-STOCK-04 — Return:** Record fish type, quantity, date/time, reason/category, and handling method for stock returned to supplier.
**FR-STOCK-05 — Return handling:** Owner can record return via driver or another method; no driver login is needed.
**FR-STOCK-06 — Expected credit:** Calculate an expected return credit using the agreed supplier rate where appropriate.
**FR-STOCK-07 — Actual credit confirmation:** Do not automatically count expected credit as received. Owner confirms or overrides the actual supplier credit/refund.
**FR-STOCK-08 — Defects before distribution:** Record defective quantities discovered before distribution.
**FR-STOCK-09 — Customer-related defects:** Optionally associate a defective quantity with a customer delivery where useful.
**FR-STOCK-10 — End-of-trip defects:** Record defective stock remaining at the end and final reconciled defective quantity.
**FR-STOCK-11 — Aggregate or detail:** Allow owner to enter a final total without entering every defective bag, while supporting optional detailed entries.
**FR-STOCK-12 — Avoid double counting:** If both detailed defect entries and a final total exist, clearly define which is the source of truth and prevent adding the same defects twice.
**FR-STOCK-13 — Stock ledger:** Every stock movement should be represented once with type, fish type, quantity, time, and source record.
**FR-STOCK-14 — Physical balance:** Calculate expected remaining stock per fish type from receipt, supplier returns, customer deliveries, and defect/other movements according to the agreed ledger convention.
**FR-STOCK-15 — Driver-reported figures:** Owner may enter quantities reported by the driver. These are a separate report, not automatically treated as correct.
**FR-STOCK-16 — Discrepancy:** Compare owner-recorded totals, physical count, and driver-reported totals; highlight differences for owner review.
**FR-STOCK-17 — Explanation and resolution:** Owner can record an explanation/resolution without erasing the original values. The application does not accuse or determine fault.
**Acceptance:** A difference between driver report and customer delivery records is visible and traceable; a return credit is not recognized as actual until owner confirms it.

### 5.9 Customer delivery and billing

**FR-DEL-01 — Customer delivery screen:** Owner can open a customer from the trip distribution list and record their delivery.
**FR-DEL-02 — Planned defaults:** Planned quantities populate the entry screen as defaults.
**FR-DEL-03 — Actual quantity:** Owner can enter more or less than planned; actual quantity controls billing and stock calculations after confirmation.
**FR-DEL-04 — Distinguish draft from confirmed:** A partially entered delivery is a draft and must not be counted as a confirmed delivery or stock movement.
**FR-DEL-05 — Explicit confirmation:** Delivery has a clear save/confirm action so unfinished work is not mistaken for completed work.
**FR-DEL-06 — Actual fish types:** Support recording actual delivered fish types and quantities per customer.
**FR-DEL-07 — Price per fish type:** Trip has a default customer selling rate per fish type.
**FR-DEL-08 — Customer override:** Owner can override selling rate for a particular customer and fish type.
**FR-DEL-09 — Preserve applied rate:** Store the actual rate applied to each delivery line. Later edits to default rates must not silently change old bills.
**FR-DEL-10 — Line total:** Calculate actual quantity × applied selling rate.
**FR-DEL-11 — Bill total:** Sum bill lines and any explicitly recorded bill adjustments.
**FR-DEL-12 — Adjustment reason:** If a manual bill adjustment is allowed, store amount, type, reason, actor, and timestamp. Exact adjustment categories can be finalized, but no silent unexplained arithmetic change is allowed.
**FR-DEL-13 — Live totals:** Update line and bill totals immediately as quantities/rates change.
**FR-DEL-14 — Draft autosave:** Persist unfinished delivery entry server-side, associated with trip/customer/owner and update time.
**FR-DEL-15 — Resume:** Owner can leave a customer, switch screens, or restart and resume a draft.
**FR-DEL-16 — Delivery and payment separate:** Delivery and payment can be recorded together or separately.
**FR-DEL-17 — Quantity comparison:** Keep planned and actual quantities available for report and review.
**Acceptance:** A draft delivery never increases confirmed sales/stock totals; a confirmed delivery uses actual quantity and the rate snapshot.

### 5.10 Payments and collection

**FR-PAY-01 — Individual payment records:** Each payment is a separate record; do not overwrite a cumulative paid amount.
**FR-PAY-02 — Payment fields:** Record amount, date/time, method, status, owner/actor, optional notes, and allocation to one or more customer trip balances.
**FR-PAY-03 — Manual payment:** Support cash and external UPI/bank payments entered by the owner.
**FR-PAY-04 — Integrated gateway later:** Design a provider adapter for online payment link/QR integration. Provider remains an open decision; use test mode during development.
**FR-PAY-05 — Gateway verification:** Initiated, failed, cancelled, or unverified gateway transactions must not reduce customer balance. Verify confirmed status server-side with the provider.
**FR-PAY-06 — Fast collection:** Payment collection should be accessible from customer profile and trip/customer screen with minimal taps.
**FR-PAY-07 — Default amount:** Suggest the relevant outstanding amount as the default; allow partial amount.
**FR-PAY-08 — Customer history:** Show all payments in one history, including amount, method, time, status, and associated trip allocation.
**FR-PAY-09 — Allocation choice:** Owner chooses which trip balance a payment applies to. UI may suggest oldest outstanding first but must let owner select another trip.
**FR-PAY-10 — Customer-specified trip:** Owner can allocate payment to a specific trip if the customer says it is for that trip.
**FR-PAY-11 — Partial payment:** Reduce the selected trip's balance by the allocated amount and leave the remainder outstanding unless owner records a valid settlement adjustment.
**FR-PAY-12 — Full settlement:** If payment clears the trip's balance, mark that trip's payment status settled.
**FR-PAY-13 — Excess payment:** Do not silently discard an overpayment. Record it as unallocated customer credit or require owner to allocate it explicitly; exact UI behavior must be selected during implementation.
**FR-PAY-14 — Confirm receipt:** Manual payment confirmation requires owner action. A UI confirmation must not be treated as proof of a gateway payment unless verified.
**FR-PAY-15 — Later payments and locked trip:** Payment recorded from customer profile updates current financial status for the corresponding trip and customer immediately without unlocking the trip or changing the historical bill/version.
**FR-PAY-16 — Payment reversal/correction:** Never delete a payment silently. Use a reversal/void record with reason and audit trail. Permission and exact reversal UX should be specified before implementation.
**Acceptance:** Old trip balance updates after a payment; locked trip's original bill and operational snapshot remain intact; failed gateway payment does not reduce receivable.

### 5.11 Outstanding debt and settlement adjustments

**FR-DEBT-01 — Per-trip balances:** Maintain each customer's outstanding amount separately by trip.
**FR-DEBT-02 — Total balance:** Customer profile shows total outstanding across trips plus per-trip detail.
**FR-DEBT-03 — Trip date:** Each outstanding entry displays its trip date and amount.
**FR-DEBT-04 — Carry forward:** Unpaid balance remains outstanding across later trips; do not count it as new sales on the next trip.
**FR-DEBT-05 — Persistent reminders:** Whenever owner opens a trip, show relevant unpaid balances and reminder notes so old debt is not forgotten. Also show debt in customer profile.
**FR-DEBT-06 — Specific unpaid flag:** Keep pending/settled status attached to the specific trip balance, not only the customer aggregate.
**FR-DEBT-07 — Owner chooses settlement treatment:** When owner decides not to pursue a remaining amount, owner chooses between discount/waived amount, no-longer-pursued amount, or leaving it outstanding.
**FR-DEBT-08 — Preserve arithmetic:** Store original bill, payments, settlement adjustments, and remaining balance separately. Do not erase a difference by marking settled.
**FR-DEBT-09 — Configurable threshold:** Owner configures a monetary threshold for cumulative settlement adjustments per customer per trip.
**FR-DEBT-10 — Cumulative rule:** Add together all relevant settlement adjustments for that customer on that trip. Require a reason only when cumulative total exceeds the configured threshold. No 80% warning; warn/require reason only when threshold is exceeded.
**FR-DEBT-11 — No splitting bypass:** Several small adjustments that cumulatively exceed the threshold trigger the same reason requirement.
**FR-DEBT-12 — Adjustment audit:** Record each adjustment separately with amount, category, reason when required, owner, timestamp, and affected trip.
**FR-DEBT-13 — Payment allocation:** Owner selects the trip allocation; default suggestion is convenience only.
**Acceptance:** A prior trip's outstanding amount remains visible even if the customer is inactive or has later trips; a settlement adjustment never alters the original bill or payment record.

### 5.12 Expenses, supplier settlement, and financial reporting

**FR-FIN-01 — Trip expenses:** Record other trip expenses with amount, category, date/time, notes, and optional reference.
**FR-FIN-02 — Supplier payable:** Record supplier invoice/amount owed and actual supplier payment(s) separately.
**FR-FIN-03 — Supplier credit/refund:** Record expected credit separately from confirmed actual credit/refund.
**FR-FIN-04 — Sales revenue:** Calculate sales from confirmed deliveries and applied selling rates/adjustments, not from cash received.
**FR-FIN-05 — Collections:** Calculate money received from confirmed payment records.
**FR-FIN-06 — Receivables:** Show unpaid customer balances separately.
**FR-FIN-07 — Supplier cost:** Show supplier cost, payments made, payable balance, and confirmed credit/refund.
**FR-FIN-08 — Other expenses:** Include confirmed trip expenses in result.
**FR-FIN-09 — Profit/loss:** Show a clearly labelled estimated/recognized trip result. Do not calculate profit as cash collected minus supplier payment alone when there are receivables, unsold stock, or other expenses.
**FR-FIN-10 — Stock/unsold treatment:** Report unsold and defective stock. Accounting treatment for inventory/cost of goods sold must be confirmed; do not silently count all received stock as cost of sold goods and also carry inventory value without a consistent policy.
**FR-FIN-11 — Customer-oriented report:** Main report prioritizes customer sales, collections, balances, quantities, and trip result. Supplier requirement/receipt detail is supporting information.
**FR-FIN-12 — Report breakdown:** Include customer sales (actual delivered quantities and amount charged), payment collections, outstanding balances by trip/customer, stock reconciliation, supplier cost/credits, other expenses, and final result.
**FR-FIN-13 — Revenue vs cash:** Clearly label revenue, cash collected, receivable, expense, and profit/loss as different metrics.
**FR-FIN-14 — Rate review:** Surface rate changes and customer-specific overrides during money reconciliation.
**Acceptance:** A report never labels collected money as profit; confirmed supplier credits are distinguished from expected credits.

### 5.13 Reconciliation and trip close

**FR-REC-01 — Bag reconciliation by fish type:** Compare quantity received, supplier returns, customer deliveries, defects, and remaining/unsold stock.
**FR-REC-02 — Physical count:** Allow owner to enter physical end count and compare against calculated expected stock.
**FR-REC-03 — Driver report:** Allow owner to enter driver-reported quantities separately and compare with owner records.
**FR-REC-04 — Differences:** Highlight differences; retain source values and allow owner to record explanations/resolution.
**FR-REC-05 — Money reconciliation:** Compare expected customer bills with payment collection and outstanding amounts. The system must not assume all sales are paid.
**FR-REC-06 — Rate review:** Owner confirms the rates and rate changes were reviewed.
**FR-REC-07 — Supplier settlement review:** Owner reviews supplier payment and actual confirmed credits/refunds.
**FR-REC-08 — Outstanding review:** Display current and prior-trip outstanding amounts before close.
**FR-REC-09 — Required confirmations:** Owner must explicitly confirm both bag and money reconciliation before trip completion.
**FR-REC-10 — Documented discrepancies allowed:** Trip may be completed with unresolved differences if the owner documents them and confirms review; the system continues to display them as unresolved.
**FR-REC-11 — Unpaid balances allowed:** Customer balances may remain outstanding after trip completion.
**FR-REC-12 — Close checklist:** Include bag reconciliation, money reconciliation, rate review, supplier settlement review, outstanding balances, and discrepancy review.
**FR-REC-13 — Close snapshot:** Completion creates an immutable version snapshot and records actor/time.
**Acceptance:** The app blocks completion if either required reconciliation confirmation is missing, but permits reviewed and documented exceptions.

### 5.14 Locking, versions, drafts, and audit

**FR-AUD-01 — Default view mode:** Opening a completed trip displays view-only mode and clearly identifies `Vn — Current` and locked status.
**FR-AUD-02 — Ordinary edit blocked:** Normal update endpoints cannot modify locked operational trip records.
**FR-AUD-03 — Owner unlock:** Only owner can unlock. Require re-authentication and a non-empty reason.
**FR-AUD-04 — Unlock event:** Record owner, timestamp, reason, prior current version, and unlock action.
**FR-AUD-05 — Draft correction:** Unlocking does not immediately create a new finalized version. Changes are saved to a separate draft as the owner works.
**FR-AUD-06 — Draft persistence:** Draft survives navigation, browser refresh, and application restart.
**FR-AUD-07 — Locked baseline:** While a correction draft exists, the last locked version remains unchanged and remains available for viewing.
**FR-AUD-08 — Save new version:** When owner finalizes/saves the correction, create a new version, preserve the prior version, and record changes.
**FR-AUD-09 — Reconcile again:** Revised trip must undergo required reconciliation review before it can be locked again.
**FR-AUD-10 — Relock:** Owner locks the revised version after review; current version label updates.
**FR-AUD-11 — Audit events:** Record sensitive changes with actor, timestamp, entity, action, before/after values or structured diff, reason when applicable, and correlation to trip/version.
**FR-AUD-12 — Append-only history:** No normal UI/API operation may delete or rewrite audit events or previous locked versions.
**FR-AUD-13 — Payment exception:** Recording a later payment updates the live financial status but does not unlock or rewrite the old trip version; payment event is separately audited.
**FR-AUD-14 — View previous versions:** Owner can inspect previous versions and compare differences against current.
**FR-AUD-15 — Draft abandon:** Owner can discard a correction draft only through an explicit action and confirmation; preserve an audit event of draft discard. The locked baseline remains.
**FR-AUD-16 — Concurrency:** Prevent stale draft saves from overwriting newer changes; use version numbers/optimistic locking.
**FR-AUD-17 — Current status clarity:** Show current version, lock state, last changed time, and whether a correction draft exists.
**Acceptance:** Unlocking and leaving without finalizing does not alter the current locked version. Saving a correction creates a new version; later payments update the live balance without changing the version's historical operational snapshot.

### 5.15 Search, dashboards, and reminders

**FR-UI-01 — Owner home:** Provide quick access to current/upcoming trips, customers, trip creation, outstanding money, and unresolved reconciliation items.
**FR-UI-02 — Outstanding reminders:** Opening a trip displays total relevant customer outstanding amounts and trip-by-trip notes.
**FR-UI-03 — Customer lookup:** Search customers quickly during distribution and payment collection.
**FR-UI-04 — Fast actions:** Common actions should require minimal taps: open customer, enter delivery, save/confirm, collect payment, return to list.
**FR-UI-05 — Live arithmetic:** Totals recalculate as entries change.
**FR-UI-06 — Clear status:** Distinguish draft, confirmed, pending payment, settled, discrepancy, completed, locked, and current version.
**FR-UI-07 — No silent defaults:** UI makes it clear when a value is a planned default rather than confirmed actual.
**FR-UI-08 — Recoverable input:** Drafted data is restored after interruptions.
**FR-UI-09 — Confirmation for consequential actions:** Confirm payment recording, settlement adjustment, trip completion, unlocking, draft discard, and relocking as appropriate.
**Acceptance:** Owner can find a customer and record a payment without navigating through trip editing/unlocking.

### 5.16 Data export, backup, and operations

**FR-OPS-01 — Database migrations:** All schema changes use Alembic migrations; do not alter production schema manually without a migration.
**FR-OPS-02 — Backup:** Provide documented database backup and restore procedure.
**FR-OPS-03 — Logging:** Log errors and operational events without leaking passwords, tokens, or sensitive secrets.
**FR-OPS-04 — Data export:** Provide a way to export important trip/customer/payment data in a human-readable format; exact formats can be finalized.
**FR-OPS-05 — Health check:** Provide a health endpoint that does not expose secrets.
**FR-OPS-06 — Time:** Store timestamps consistently (prefer UTC in persistence) and display local time in the owner's configured timezone.
**FR-OPS-07 — Decimal arithmetic:** Use decimal/numeric types for currency and rates; never binary floating-point for money.
**FR-OPS-08 — Input validation:** Reject negative quantities, invalid amounts, invalid state transitions, and malformed records. Zero quantities may be permitted only where business meaning is explicit.
**Acceptance:** Backup can be restored in a documented test; currency arithmetic is deterministic.

## 6. Business rules and calculation conventions

### 6.1 Quantity reconciliation
For each fish type, maintain distinct quantities for:
- Actual supplier receipt.
- Returns to supplier.
- Confirmed customer deliveries.
- Defects/other explicitly classified losses.
- Physical remaining/unsold stock.
- Driver-reported values (informational comparison, not automatically authoritative).

A candidate stock equation is:

`Expected remaining = received - supplier returns - confirmed customer deliveries - quantities classified as disposed/lost`

The exact treatment of defective stock depends on whether defects are still physically on hand or disposed/returned. Defective stock must not be subtracted twice. If defects remain physically present, show them as a category within remaining stock; if discarded/returned, record the corresponding movement. The UI should expose the component totals and discrepancy rather than hide the arithmetic.

### 6.2 Customer billing
For each confirmed delivery line:

`Line total = actual quantity × applied selling rate`

`Bill total = sum(line totals) + explicitly recorded bill adjustments`

`Trip outstanding = bill total - payments allocated to this trip - valid settlement adjustments`

Do not let a settlement adjustment rewrite the original bill. Keep bill, payments, adjustments, and balance separate.

### 6.3 Payment allocation
A payment is a financial event. Allocation applies the payment to a specific trip receivable. If one payment is split across trips, store allocation rows whose total cannot exceed the payment amount. The owner selects the allocation. Overpayment behavior must be explicitly handled; do not silently discard it.

### 6.4 Supplier settlement
Track supplier cost/amount payable, supplier payment transactions, expected return credit, and confirmed actual credit/refund separately. Do not automatically assume the supplier gave a refund or credit.

### 6.5 Profit/loss
At minimum, show clearly separate:
- Sales/revenue from confirmed delivery bills.
- Cash/payment collections.
- Customer receivables.
- Supplier cost/payments/payable.
- Confirmed supplier credits/refunds.
- Other trip expenses.
- Unsold/defective stock.

A simple cash view may show collections minus cash expenses, but it must not be labelled profit. The recognized profit calculation requires a consistent inventory/cost-of-goods-sold policy. For MVP, report the operational result with transparent inputs and label any provisional calculation. Final inventory accounting treatment is an open decision.

### 6.6 Settlement adjustment threshold
The owner configures a currency threshold. Sum waived/no-longer-pursued adjustments for each customer within one trip. If cumulative adjustment **exceeds** the threshold, a reason is required before confirming the adjustment. At or below the threshold, no warning/reason requirement is imposed by this rule. No 80% warning is needed. The threshold is per customer per trip; historical adjustments remain visible.

## 7. Data integrity and audit requirements

- Use database transactions for actions that must be atomic, such as confirming a delivery and its stock movement, saving a payment and its allocation, finalizing a trip version, and recording a supplier return with related credit expectation.
- Use unique identifiers for records.
- Keep monetary amounts in decimal columns with an explicit currency.
- Keep measurement units explicit. Initial quantity unit is bags; do not silently mix units.
- Preserve snapshots for supplier sent revisions and locked trip versions.
- Record all meaningful edits to financial/stock records with before/after values.
- Use soft deactivation for master data referenced by history.
- Protect audit data from ordinary update/delete paths. Stronger tamper evidence (e.g., hash chaining or external append-only storage) is a future security decision, not assumed implemented by a normal audit table.
- Avoid double-counting by ensuring a movement has one canonical source and a unique link to the event that generated it.
- Use idempotency keys or duplicate-submit protection for payment and confirmation endpoints where practical.

## 8. Non-functional requirements

### NFR-01 — Speed
Common customer lookup, delivery entry, and payment actions should be optimized for minimal interaction. Establish measurable response-time targets after choosing deployment hardware and frontend. Avoid unnecessary multi-step forms.

### NFR-02 — Reliability
Persist drafts server-side. Failed operations must not leave partial financial/stock transactions.

### NFR-03 — Correctness
Use database constraints, service-layer rules, decimal arithmetic, and tests for all financial/quantity calculations.

### NFR-04 — Security
Hash passwords, protect secrets, authorize every write, validate inputs, and avoid exposing stack traces or credentials.

### NFR-05 — Auditability
Completed versions and audit entries are immutable through normal application behavior. Changes to historical data are explicit and traceable.

### NFR-06 — Usability
Readable labels, visible current version, clear draft/confirmed distinction, and actionable discrepancy summaries.

### NFR-07 — Maintainability
Separate API, schema, domain/service, and persistence concerns. Reuse patterns consistently without prematurely building a generic framework for every possible future feature.

### NFR-08 — Recoverability
Document backups, restoration, migrations, and draft recovery. Test restore procedure before production use.

### NFR-09 — Compatibility
Automated tests should run reliably. SQLite may be used for simple unit/integration tests, but PostgreSQL integration tests are required for production-critical behavior and constraints.

### NFR-10 — Privacy
No external user portal. Do not include secrets or unnecessary personal information in logs. Keep customer contact data available only to the owner.

## 9. Important states and transitions

Exact names can be normalized during implementation, but equivalent behavior is required.

### Trip lifecycle
- **Draft/Planning:** customer list and planned quantities are being prepared.
- **Planned:** supplier requirement may be prepared/sent; plan is ready for operations.
- **Distributing:** receiving/delivery operations are underway.
- **Reconciling:** owner reviews quantities and money.
- **Completed/Locked:** required reconciliations confirmed; current version immutable.
- **Unlocked correction:** a separate correction workspace exists; locked baseline remains immutable.
- **Draft correction:** saved working changes exist but are not the finalized current version.

Block invalid transitions. For example, do not mark a trip complete before both reconciliation confirmations. A completed trip is viewed by default; ordinary edit requests must fail.

### Delivery
- Draft/in progress.
- Confirmed.
- Corrected only through permitted trip correction process after lock; maintain history.

### Payment
- Manual payment pending owner confirmation or confirmed according to UX.
- Gateway initiated/pending.
- Gateway confirmed only after server verification.
- Failed/cancelled/reversed.
- Allocated/unallocated as a separate allocation state where needed.

### Supplier requirement
- Draft.
- Sent revision (immutable snapshot).
- New draft/revision when changed after sending.
- Do not represent supplier acceptance unless a future confirmation feature is added.

## 10. Acceptance scenarios

1. Create a new trip using last trip's customer list; all planned quantities start blank/unset, not copied.
2. Add a customer omitted from the previous trip.
3. Aggregate planned quantities by fish type, then override the requested supplier quantity; both values and their difference remain visible.
4. Mark supplier requirement sent; change it later; earlier revision remains unchanged and new revision is created.
5. Receive fewer bags than requested; system highlights the variance.
6. Enter a delivery draft and leave the screen; it remains a draft and is not included in confirmed stock/sales.
7. Confirm a delivery with actual quantities different from planned; bill and stock use actual quantities, while planned values remain available.
8. Change a customer-specific selling rate; applied rate is preserved on the bill and rate change is visible at reconciliation.
9. Record partial payment; payment history grows by one transaction and only selected trip balance decreases.
10. Record a later payment for an old trip from customer profile; old trip balance updates immediately without unlocking or changing its locked bill/version.
11. Mark a small remainder waived; preserve original bill/payment and record adjustment separately.
12. Create multiple adjustments that cumulatively exceed threshold; reason becomes mandatory when crossing the threshold.
13. Compare received, returned, delivered, defective, and remaining quantities; show discrepancy without assuming blame.
14. Enter a driver-reported count that differs from owner records; retain both values and allow explanation/resolution.
15. Attempt to close trip without bag reconciliation confirmation; reject.
16. Attempt to close trip without money reconciliation confirmation; reject.
17. Close with documented discrepancy and unpaid customer balances after required confirmations; allow close and keep reminders visible.
18. Open completed trip; view-only screen clearly says `Vn — Current` and `Locked`.
19. Attempt ordinary API update to locked trip; reject.
20. Unlock without fresh authentication or reason; reject.
21. Unlock, edit draft, leave without finalizing; current locked version remains unchanged and draft is recoverable.
22. Save correction; create next version and audit diff; prior version remains viewable.
23. Re-lock only after required reconciliation review.
24. Try to delete or alter audit history through normal API; reject.
25. Verify report shows sales, collections, receivables, supplier payments/cost, credits, expenses, inventory/unsold stock, and profit separately.
26. Verify decimal calculations and transaction rollback on failed writes.
27. Restore a database backup in a test environment using documented steps.

## 11. Open decisions (do not invent answers)

The following are deliberately unresolved and should be decided when needed:
1. Frontend framework and deployment approach.
2. Payment provider, gateway fees, and exact online link/QR workflow.
3. Final inventory accounting policy and cost-of-goods-sold calculation, including valuation of unsold stock.
4. Exact treatment of overpayments and unallocated customer credit UX.
5. Whether partial payment plus settlement requires additional confirmation/receipt format.
6. Exact master-data fields beyond those already required operationally.
7. Currency/timezone settings (likely INR and India local time, but make configurable).
8. Whether export is CSV, PDF, Excel, or a combination.
9. Exact audit tamper-evidence requirement beyond append-only application behavior.
10. How to reverse a wrongly recorded manual payment and who may authorize it (owner only in current scope, but UX should be confirmed).
11. Whether to support quantities other than bags or fractional bags.
12. Whether customer delivery can be split into multiple delivery records for one customer in a trip.
13. Whether supplier payment can be split across multiple payments and how to handle advances.
14. Exact operational fields for expenses, driver report, defect categories, and return methods.
15. Exact trip status names and whether a new trip can be edited after supplier requirement is sent other than through revisions.
16. Backup frequency, retention, and deployment environment.

Do not block the initial core vertical slice on every open item. Implement the confirmed rules and keep uncertain behavior behind explicit decisions/configuration.
