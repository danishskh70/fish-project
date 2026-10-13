# Build Plan — Fish Seed Distribution Management App

## 1. Purpose

Define the implementation sequence from the current learning project to the complete application.

The final product requirements and target architecture are documented separately. This file controls implementation order, dependencies, and completion checkpoints.

Do not interpret a later phase as permission to implement it early.

## 2. Build Rules

- Implement one focused learning objective at a time.
- Prefer small vertical slices that can be run and verified.
- Do not build a large framework before proving the pattern with real examples.
- Do not implement business behavior before the relevant requirements are clear.
- Do not skip required validation, authorization, or tests merely to reach the next feature.
- Update `CURRENT_TASK.md` after completing a checkpoint.
- Record durable design decisions in `DECISIONS.md`.
- Mark a feature complete only after verification.

## 3. Phase 0 — Project Foundation

### Objective

Create a working development environment and understand the application entry point.

### Work

- Initialize the Python project using `uv`.
- Install FastAPI and Uvicorn.
- Create the FastAPI application entry point.
- Add a health endpoint.
- Run the application locally.
- Verify the endpoint through Swagger UI or an HTTP request.
- Understand how the application registers routers.

### Completion criteria

- The application starts successfully.
- The health endpoint returns the expected response.
- The learner can explain the purpose of the entry point and router registration.

### Status

Completed for the current basic setup. Preserve the actual verified route and response in `CURRENT_TASK.md`.

## 4. Phase 1 — Understand and Design the Generic Record Engine

### Objective

Understand what a record represents and why reusable record operations are useful.

### Work

1. Define the meaning of a record in the architecture.
2. Design `Field`.
3. Design `RecordSpec`.
4. Determine which behavior belongs in a specification and which belongs in a service.
5. Review the design against a placeholder `Request` record.
6. Identify what should remain generic and what should remain domain-specific.

### Constraints

- Do not implement the complete engine before the concepts are understood.
- Do not build the database table builder, authentication system, or fish-specific workflows in this phase.
- Do not assume the placeholder `Request` is part of the final business domain.

### Completion criteria

- The learner can explain the purpose of `Field` and `RecordSpec`.
- The design has a clear responsibility for each component.
- The proposed specification can describe a simple record without embedding an entire business workflow.

## 5. Phase 2 — Prove the First Generic Record

### Objective

Turn the specification into a functioning record without prematurely generalizing everything.

### Work

- Define the first record's input and output contracts.
- Implement the minimum persistence needed.
- Implement a record service.
- Expose a small set of API operations.
- Verify successful operations and failure behavior.
- Add tests for validation and data integrity.

### Completion criteria

The first record can be created, retrieved, and otherwise managed only to the extent supported by the confirmed design.

The learner can trace a request through the API, service, and persistence layer.

## 6. Phase 3 — Validate Reuse

### Objective

Determine whether the architecture genuinely supports more than one record type.

### Work

- Add a second small test record.
- Reuse the same generic mechanism.
- Identify differences that require configuration versus domain-specific behavior.
- Refine the abstraction only where actual evidence justifies it.
- Test the behavior of both records.

### Completion criteria

The second record uses the reusable pattern without copy-pasting the entire implementation or introducing unrelated complexity.

## 7. Phase 4 — First Real Business Vertical Slice: Product Master

### Objective

Implement fish seed types using the verified record-engine pattern.

### Work

- Define the fish seed type fields and validation.
- Define the persistent model.
- Connect the domain specification to the record engine.
- Expose the API.
- Build a React list screen.
- Build a React create/edit form.
- Connect the frontend to the API.
- Verify persistence and validation.
- Test invalid input and expected error responses.

### Constraints

- Fish seed types must be entered and maintained through the application.
- Do not hardcode the seed catalog in the frontend.
- Do not add unrelated booking, procurement, or financial workflows to this slice.

### Completion criteria

The owner can manage fish seed types through the React interface, and changes persist correctly.

## 8. Phase 5 — Authentication and Protected Access

### Objective

Protect the application using the agreed authentication model.

### Work

- Finalize the owner-account and initial WRITER-role design.
- Define credential storage and authentication behavior.
- Implement Bearer JWT authentication.
- Protect the required endpoints.
- Derive the authenticated identity on the backend.
- Test unauthenticated and unauthorized requests.
- Integrate login state into React.

### Completion criteria

Protected operations cannot be accessed without valid authentication, and identity-sensitive behavior does not trust client-supplied identity.

## 9. Phase 6 — Reference Data and Domain Foundation

### Objective

Build the remaining necessary business records and relationships.

### Work

- Finalize the domain model.
- Implement customer records.
- Implement supplier records if required by the confirmed model.
- Implement pricing configuration and historical rate handling.
- Define database constraints and migrations.
- Establish common validation and error-handling patterns.
- Verify relationships and ownership rules.

### Completion criteria

Reference data can be managed through the UI and API with tested relationships and constraints.

## 10. Phase 7 — Customer Booking Workflow

### Objective

Support customer bookings and their lifecycle.

### Work

- Define booking and booking-line entities.
- Define booking statuses and valid transitions.
- Record multiple seed types and quantities per booking.
- Record applicable selling rates.
- Record relevant customer and distribution details.
- Add advance and payment associations.
- Test booking creation, changes, and permitted cancellation behavior.

### Completion criteria

The booking lifecycle follows confirmed business rules and preserves the original transaction information needed for later reconciliation.

## 11. Phase 8 — Procurement and Trip Planning

### Objective

Group demand into trips and coordinate planned quantities with the supplier.

### Work

- Define trip and procurement records.
- Calculate planned quantities by seed type.
- Record expected dates and supplier coordination.
- Implement the agreed booking-to-trip relationships.
- Handle rescheduling and cancellation.
- Define valid workflow transitions.
- Test quantities and related booking effects.

### Completion criteria

The owner can prepare and manage a trip without losing booking or procurement history.

## 12. Phase 9 — Arrival, Inspection, and Inventory

### Objective

Record what physically arrives and what is accepted.

### Work

- Record actual quantities by seed type.
- Record accepted and rejected quantities.
- Implement quality and defect records.
- Apply the agreed supplier-cost treatment.
- Track inventory movements.
- Test discrepancies between planned and actual quantities.

### Completion criteria

The application distinguishes planned, received, accepted, and rejected quantities and preserves a reconcilable inventory history.

## 13. Phase 10 — Shortage Allocation and Excess Handling

### Objective

Support owner-controlled decisions when actual supply differs from demand.

### Work

- Calculate shortages by seed type.
- Present affected bookings and available quantities.
- Record the owner's allocation decisions.
- Record additional sales or other approved excess outcomes.
- Preserve original bookings and decision history.
- Test that the system never silently allocates shortages.

### Completion criteria

All affected quantities are traceable to recorded decisions and resulting movements.

## 14. Phase 11 — Distribution and Sales

### Objective

Complete distribution at the planned spots.

### Work

- Define distribution spot records.
- Record attendance and customer deliveries.
- Handle partial deliveries and agreed carry-forward rules.
- Record additional quantities sold.
- Record walk-in sales.
- Record quantities retained for the owner's pond.
- Track remaining quantities and waste.
- Test quantity reconciliation.

### Completion criteria

The system can explain where each relevant quantity went and which customer or business outcome it belongs to.

## 15. Phase 12 — Customer Payments and Balances

### Objective

Track money received and customer obligations accurately.

### Work

- Implement payment records.
- Support approved payment methods.
- Associate payments with the appropriate business transactions.
- Calculate advances, payments, and remaining balances.
- Handle the agreed refund, reversal, and credit rules.
- Test partial payments and reconciliation.

### Completion criteria

Customer balances can be reproduced from recorded financial transactions.

## 16. Phase 13 — Defects, Complaints, and Waste

### Objective

Handle defects discovered at different points in the distribution lifecycle.

### Work

- Record defects and waste with relevant context.
- Support owner-selected complaint resolutions.
- Track quantity and financial effects.
- Handle defects discovered after distribution.
- Define and test the effect of late discoveries on inventory and supplier settlement.

### Completion criteria

The system preserves defect history and applies the confirmed financial treatment without duplicate deductions.

## 17. Phase 14 — Supplier Settlement

### Objective

Calculate and record the final supplier obligation.

### Work

- Calculate accepted seed costs by type.
- Add vehicle charges.
- Account for supplier advances and approved deductions.
- Record supplier payments and remaining balances.
- Implement settlement states.
- Handle corrections according to the approved rules.
- Test calculations against known examples.

### Completion criteria

Every settlement is reproducible from recorded quantities, rates, charges, advances, deductions, and payments.

## 18. Phase 15 — Reports and Reconciliation

### Objective

Provide an accurate end-of-trip operational and financial view.

### Work

- Report quantities by seed type.
- Reconcile deliveries, additional sales, waste, rejected quantities, and remaining inventory.
- Report online and offline collections.
- Report customer balances.
- Report supplier settlement and outstanding amounts.
- Implement the approved definition of financial results.
- Test report totals against source records.

### Completion criteria

Reports agree with the underlying transactions and do not count the same quantity or financial movement twice.

## 19. Phase 16 — Hardening and Production Readiness

### Objective

Make the application reliable and maintainable.

### Work

- Expand automated test coverage.
- Verify transaction boundaries and rollback behavior.
- Review authorization and input validation.
- Review logging and audit history.
- Add database migration procedures.
- Establish backup and restore procedures.
- Decide deployment configuration.
- Add production error handling and operational monitoring.
- Verify recovery from failure scenarios.

### Completion criteria

The application meets the agreed reliability, security, backup, and deployment requirements.

## 20. Phase Management

Each phase must have:

- A clear objective
- A bounded scope
- Confirmed requirements
- An implementation task
- Verification steps
- Explicit completion criteria

When a phase is complete, update `CURRENT_TASK.md` and record any durable decisions.

A phase is not complete merely because the code runs. The intended behavior must be verified.
