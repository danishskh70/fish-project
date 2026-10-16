# Distribution Lifecycle Requirements Addendum

Status: **Confirmed by owner — 2026-10-15**

This addendum records decisions made specifically for the distribution lifecycle. Where it conflicts with older delivery requirements (especially persistent delivery drafts), this addendum supersedes the older wording for distribution entry. Payment behavior remains out of the current implementation scope.

## 1. Distribution submission

- Distribution entry has no saved draft in the first version. Nothing is persisted as a distribution until the owner presses **Submit**.
- A submission can contain multiple fish-type line items.
- Submission is atomic: all distribution line items and related stock/customer-history effects are committed together, or none are.
- Repeated submission/retry of the same action must not create a duplicate distribution or apply stock effects twice (idempotent submission).
- Each submitted distribution receives a unique reference. Show the customer, trip, and date alongside the reference.
- A distribution is a confirmed business transaction once submitted.

## 2. Quantities and handovers

- Preserve the customer's original requested quantities independently from actual distributed quantities.
- The owner records actual quantities, which may be higher or lower than requested.
- Allow zero-quantity line items so the owner can record that none of a requested fish type was delivered.
- The owner may add a fish type to a distribution if that fish type is planned for the trip, even when the customer did not request it. Do not rewrite the original request.
- If actual quantity exceeds the original request, show requested quantity, entered quantity, and excess, and require explicit owner confirmation before submission.
- If calculated available stock is insufficient, show the available quantity and shortfall and require explicit owner confirmation. Do not block the distribution solely because calculated stock is insufficient; the purchasing list or starting stock may be wrong.
- Calculated stock may become negative. Flag the discrepancy immediately; negative calculated stock is a signal to investigate, not proof that the actual distribution was wrong.
- Multiple handovers to one customer are allowed. Record each handover as a separate distribution with its own reference. Calculate cumulative quantities across handovers; do not overwrite the earlier handover.
- If a line was marked final for the trip and another handover is later needed, allow it after a warning and explicit confirmation. Preserve the earlier decision and flag it as superseded.

## 3. Outstanding customer quantities and next-trip selection

- At submission, the owner decides separately for each fish-type line whether an unfulfilled quantity remains outstanding or is final for the trip.
- Trip completion may proceed while customer quantities remain outstanding, provided the owner acknowledges them in the completion checklist.
- Outstanding quantities remain associated with the original trip and remain visible in its history.
- Outstanding quantities must be remembered and presented as candidates in the next-trip customer/requirement list.
- They must **not** be carried forward automatically. For each candidate outstanding quantity, the owner decides whether to include it in the next trip's list or omit/remove it from that new list.
- Including or omitting a quantity in the next trip must not alter the completed trip's original request, distribution, or outstanding history.
- Do not assume an outstanding quantity is still wanted without the owner's explicit next-trip decision.

## 4. Stock starting point, adjustments, and discrepancies

- Packing-list quantity is the default starting stock for each fish type; the owner may adjust it before distribution begins.
- Stock adjustments are allowed at any time, including after trip completion, and require a reason.
- Support both adjustment entry methods:
  1. enter a signed quantity difference; or
  2. enter a physical count and let the app calculate the adjustment.
- After the owner confirms a physical count, apply the calculated adjustment immediately and create a separate adjustment record.
- Do not edit or delete a previously confirmed stock adjustment to correct it. Create a new corrective adjustment with a reason.
- Flag negative calculated stock immediately for the affected fish type/trip.
- A stock discrepancy requires an explicit review outcome (for example, purchasing-list error, starting-stock error, or other) and an optional explanatory note; require a note for "other".
- Recording a review outcome does not silently change stock or rewrite distribution records. Preserve the discrepancy and review history.
- During trip completion, show remaining stock, outstanding quantities, reconciliation status, and unresolved discrepancies.
- Completion may proceed with unresolved discrepancies after explicit owner acknowledgement. Preserve their visibility in completed-trip history.

## 5. Reversals and replacements

- Correct an incorrect distribution using reversal plus replacement; do not silently edit the original transaction.
- Preserve the original distribution, reversal, and replacement as linked history.
- A distribution may be reversed only once.
- Reversal requires a reason category. Require a written explanation for "other"; allow an explanatory note for other categories when needed.
- A wrong-customer distribution uses the same reversal-and-replacement process.
- A reversal restores the original distribution's stock effect; the replacement applies its own stock effect.
- Reversing a distribution from a completed trip does not reopen the trip. Record the reason, update calculated stock, preserve history, and flag the completed trip as changed.
- A completed trip blocks normal distribution activity but still permits explicit reversals and stock adjustments with reasons.

## 6. Customer history

- Customer profile shows cumulative net totals per fish type across trips and the underlying trip-by-trip distribution history.
- Net totals account for reversals and replacements; reversed quantities must not inflate totals.
- Detailed history retains the original distribution, reversal, and replacement.

## 7. Trip completion

- The owner reviews a completion checklist covering remaining stock, outstanding customer quantities, reconciliation status, and unresolved discrepancies.
- One final **Complete Trip** action confirms completion and records the completion timestamp.
- The owner must explicitly acknowledge outstanding quantities and unresolved discrepancies before completion.
- Completion does not imply that stock has been physically verified or that all outstanding quantities have been fulfilled.
- After completion, block normal distributions; permit only the previously specified reversal and stock-adjustment workflows with reasons.

## 8. Audit and scope

- A future audit table should record each confirmation/action with a timestamp. This is a future requirement, not a claim that the audit table already exists.
- Payment functionality is out of the current distribution implementation scope and is planned as a later feature alongside distribution.
- Do not invent additional business rules. Mark unresolved decisions as open and ask the owner when a decision affects implementation.
"""

decisions = r"""# DECISIONS.md — Fish-project

This file records confirmed business and product decisions. It is not a record of implementation completion. A confirmed requirement does not mean code, database schema, migrations, tests, or UI have been implemented.

## Distribution lifecycle — confirmed 2026-10-15

### Submission and record identity
- No saved distribution drafts in the first version; only Submit creates a distribution.
- One submission may contain multiple fish-type line items.
- Submission is atomic across distribution lines and related stock/customer-history effects.
- Repeated submission of the same action must not duplicate the distribution or its stock effect.
- Every distribution has a unique reference, displayed with customer, trip, and date.
- Each handover is a separate distribution record; cumulative totals are calculated across handovers.

### Quantities
- Original requested quantities and actual distributed quantities are separate and preserved.
- Zero-quantity lines are allowed.
- A fish type can be added to a distribution if it is planned for the trip, even if not in the original request.
- Excess over the original request is allowed only after warning and explicit confirmation.
- Insufficient calculated stock is a warning, not a hard block; require explicit confirmation and allow calculated stock to become negative.
- Negative stock is flagged immediately and reviewed; it does not by itself prove the distribution was wrong.

### Outstanding quantities and next trip
- Outstanding/final status is chosen per fish-type line.
- A later handover after a line was marked final is allowed after warning and confirmation; preserve and flag the earlier decision as superseded.
- Trip completion is allowed with outstanding quantities after explicit acknowledgement.
- Outstanding quantities remain in the original trip's history.
- Outstanding quantities are shown as candidates when preparing the next trip, but are never carried forward automatically.
- The owner explicitly chooses whether each candidate quantity is included in or omitted from the next trip's list. This choice does not rewrite the previous trip.

### Stock and reconciliation
- Packing-list quantity is the default starting stock; owner may adjust it before distribution begins.
- Stock adjustments are allowed even after trip completion and require reasons.
- Support signed-difference and physical-count adjustment entry.
- A confirmed physical count applies its adjustment immediately.
- Correct an incorrect adjustment by adding a new corrective adjustment, never by silently editing the previous record.
- Negative stock requires an explicit review outcome; "other" requires an explanatory note. Review does not itself alter stock.
- Completion checklist includes remaining stock, outstanding quantities, reconciliation status, and unresolved discrepancies.
- Trip completion can proceed with unresolved discrepancies after explicit acknowledgement.

### Reversals and history
- Correct distributions by reversal plus replacement; preserve all records and their relationship.
- Each distribution can be reversed only once.
- Reversal requires a reason category; "other" requires a written explanation.
- Wrong-customer corrections use reversal plus replacement.
- Reversal of a completed-trip distribution does not reopen the trip; flag the completed trip as changed.
- Completed trips block normal distribution but allow reversals and stock adjustments with reasons.
- Customer history shows both cumulative net totals per fish type and trip-by-trip detail. Totals account for reversals.

### Completion and scope
- One final Complete Trip confirmation records completion time and blocks normal distribution.
- Outstanding quantities and unresolved discrepancies require acknowledgement, not automatic resolution, before completion.
- A timestamped audit table for every confirmation/action is a future requirement; it is not yet implemented.
- Payment functionality is deferred from the current distribution scope and planned for later.

## Documentation conflict note

The prior requirements draft contains older wording about delivery drafts persisting across screen changes and app restarts. For distribution entry, that conflicts with the confirmed "no saved drafts" decision above. The new distribution-specific rule supersedes that older wording. Do not apply the no-draft rule to unrelated workflows unless separately decided.

## Implementation status

These decisions are documented as business requirements only. Before implementation, update the architecture and build plan to describe the required distribution, stock-movement, reversal, and outstanding-quantity records and workflows. Do not claim those structures exist until verified in code.
"""

build_addendum = r"""# Build Plan Addendum — Distribution Lifecycle

Status: requirements confirmed; implementation not yet verified.

Add this work after the existing trip, supplier-list, and packing-list workflows. Do not implement payment functionality as part of this slice.

## Suggested distribution implementation sequence

1. **Inspect and align existing models**
   - Verify the current trip, packing-list, customer requirement, and fish-type models.
   - Decide exact persistence structures only after inspection; do not assume these records already exist.
2. **Distribution record and line items**
   - Parent distribution with unique reference, trip/customer/date, status, and timestamps.
   - Multiple fish-type line items preserving actual quantities and the per-line outstanding/final decision.
   - Preserve original customer requirements independently.
3. **Stock movement and starting stock**
   - Initialize available calculated stock from packing-list quantities, with owner adjustment before distribution starts.
   - Use explicit stock movements for distributions, reversals, and adjustments so each effect is traceable.
4. **Atomic submission and duplicate protection**
   - Commit all lines and stock effects in one database transaction.
   - Add idempotent retry protection so a repeated request does not duplicate the transaction.
5. **Warnings and confirmations**
   - Excess-over-request confirmation.
   - Insufficient-stock confirmation; permit negative calculated stock.
   - Warn when adding a handover after the line was marked final.
6. **Outstanding quantities in next-trip planning**
   - Present previous-trip outstanding quantities as candidates.
   - Require the owner to explicitly include or omit each candidate for the new trip.
   - Never mutate the original trip's history.
7. **Reversal and replacement**
   - Preserve and link original, reversal, and replacement records.
   - Enforce one reversal per distribution.
   - Require reason category and explanatory text for "other".
   - Allow reversal after completion without reopening the trip.
8. **Stock adjustments and discrepancy review**
   - Signed difference and physical-count modes.
   - Apply confirmed count immediately.
   - Correct prior adjustments with new adjustment records.
   - Record discrepancy review outcomes without silently altering stock.
9. **Customer history and trip completion**
   - Net totals per fish type plus detailed trip-by-trip history.
   - Completion checklist and explicit acknowledgement of outstanding quantities/discrepancies.
   - Complete Trip records timestamp and blocks normal distribution.
10. **Tests and verification**
   - Test transaction atomicity, duplicate submission, stock calculations, negative stock, excess confirmation, zero quantities, multiple handovers, reversal constraints, completed-trip behavior, outstanding carry-forward selection, net totals, and completion acknowledgements.
   - Run the repository's documented test, lint, migration, and diff checks before committing.

## Architecture review checkpoints

Before coding, document how the current project architecture will support:
- distribution parent/line records;
- append-only stock movements and corrections;
- idempotent submission;
- reversal linkage and one-reversal constraint;
- outstanding quantity selection for a future trip;
- discrepancy review and completion acknowledgement.

These are design needs, not claims about the current schema.
"""

readme = r"""# Fish-project distribution documentation patch

This patch captures the distribution lifecycle decisions confirmed with the owner on 2026-10-15.

## Files
- `REQUIREMENTS_distribution_addendum.md`: append to the existing `REQUIREMENTS.md`, and treat it as authoritative for distribution-entry conflicts.
- `DECISIONS.md`: add at the project root as the decision log.
- `BUILD_PLAN_distribution_addendum.md`: merge into the existing `BUILD_PLAN.md` after inspecting the current implementation.
- `ARCHITECTURE_REVIEW_NOTES.md`: checklist for reviewing the existing architecture without claiming unverified schema details.

## Important limitation
These files were prepared from the prior documentation available in this conversation. They have not been written into the local directory `~/projects/fish-project`, and they have not been tested against the current working tree. Review and merge them locally before implementation.
"""

architecture_notes = r"""# Architecture Review Notes — Distribution Lifecycle

The current architecture document and working tree must be inspected before proposing concrete model or service changes. The following are required capabilities, not confirmed existing components.

- Distribution submission must be atomic across the parent record, line items, stock effects, and customer-history calculations.
- Duplicate retries must not create a second business transaction.
- Stock should be explainable from an opening balance plus explicit movements, including distribution, reversal, and adjustment effects.
- Reversals must reference the original distribution and be limited to one reversal per distribution.
- Replacement distributions must be separate records.
- Outstanding quantities must remain associated with the original trip; next-trip inclusion/omission is an explicit new-trip decision.
- Completed trips must block normal distribution while permitting authorized reversal and adjustment operations with reasons.
- Stock discrepancy review must be recorded separately from stock-changing operations.
- Customer totals must be calculated net of reversals while preserving transaction-level history.

Before implementation, map each capability to the existing `RecordSpec`/`RecordService` architecture where appropriate, and use custom workflow services for multi-record transactions and lifecycle rules. Do not force a multi-record distribution workflow into generic CRUD if doing so obscures its invariants.
"""
