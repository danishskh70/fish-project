# Business Requirements — Fish Seed Distribution Management App

## 1. Purpose

Define the complete intended business behavior of the Fish Seed Distribution Management App.

This document describes what the application must support, independently of how it is implemented.

Requirements marked `CONFIRMED` reflect decisions already made. Requirements marked `OPEN` need further clarification. Do not treat an open question as permission to invent a rule.

## 2. Business Overview

The owner coordinates fish seed purchases from suppliers and distributes the seed to customers at scheduled distribution spots.

The general business flow is:

1. Record customer bookings.
2. Group bookings into a planned procurement trip.
3. Determine the quantities required by seed type.
4. Coordinate the trip with the supplier.
5. Record the actual arrival and accepted quantities.
6. Allocate available quantities and distribute seed.
7. Record customer payments, shortages, excess seed, and defects.
8. Reconcile customer balances and supplier accounts.
9. Complete financial settlement and retain an operational history.

The actual process may involve date changes, cancellations, shortages, excess quantities, rejected seed, waste, and outstanding payments.

The application must represent these situations explicitly rather than assuming every trip follows the ideal path.

## 3. People and Access

### 3.1 Business owner

- The owner is the primary authenticated user.
- The owner performs and authorizes operational actions.
- The owner enters customer, supplier, driver, booking, trip, payment, and settlement information.
- The owner makes allocation and exception-handling decisions.

### 3.2 External participants

Customers, suppliers, drivers, and walk-in buyers are recorded as business data.

They do not automatically receive application accounts.

### 3.3 Authentication and authorization

- The API will use Bearer JWT authentication.
- The WRITER role is required for the initial record-engine learning implementation.
- The final business application initially has one owner account.
- The relationship between the initial WRITER role and the final owner-only account model must be documented when authentication is implemented.
- Do not create a general multi-role employee system without an approved requirement.

## 4. Customers

The customer record must support:

- Customer name
- Mobile number
- Address

A customer may make multiple bookings over time.

Customer identity and contact information should be reusable across bookings rather than copied into a new customer record for every transaction.

The required uniqueness rules for mobile numbers, duplicate customers, and changes to customer details remain open.

## 5. Fish Seed Types and Pricing

### 5.1 Seed type master

The owner must be able to create and maintain fish seed types through the application.

Seed types are business records, not hardcoded frontend options.

The application must support a reusable product-master concept that can later be extended with domain-specific fields and actions.

### 5.2 Quantity unit

- The business tracks quantities in bags.
- A bag contains approximately 250 seeds, but the actual number varies with seed size.
- Do not calculate or promise an exact number of seeds per bag.
- The operational quantity unit is the bag.
- Do not introduce per-seed inventory calculations unless separately approved.

### 5.3 Selling prices

- A standard selling rate may be configured for each seed type.
- The standard rate applies to smaller quantities.
- Larger quantities may receive an individual rate.
- A special selling rate may be set when recording a booking or selling seed at a distribution spot.
- The owner determines the applicable rate.

The exact threshold for a larger quantity and the pricing precedence rules are open.

Historical transactions must preserve the rate actually applied to them. Editing a current standard rate must not silently change the financial value of an earlier booking or completed sale.

### 5.4 Supplier buying rates

- The supplier buying rate is recorded per seed type.
- The rate is generally fixed and changes rarely.
- The buying rate used for a procurement transaction must be retained for that transaction.

The rules for multiple suppliers, supplier-specific rates, and rate changes during an active trip remain open.

## 6. Customer Bookings

### 6.1 Booking creation

- The owner speaks with customers and advises them personally.
- The system does not recommend or calculate how much seed a customer should buy.
- Only confirmed customer bookings are recorded as bookings.
- A customer may book multiple seed types.
- Each seed type has its own booked quantity.
- Quantities are recorded in bags.
- The owner communicates the distribution date, time, and place to the customer.
- An advance may be collected after the supplier provides a truck date and the owner informs the customer.

The application must distinguish a booking from a payment and from a completed delivery.

### 6.2 Booking information

A booking needs to identify:

- Customer
- One or more seed types and quantities
- Applicable selling rates
- Relevant trip or distribution arrangement
- Agreed date, time, and place as applicable
- Advance amount and payment records, when applicable
- Current booking status

The precise booking schema and required fields at each status transition remain to be finalized.

### 6.3 Booking changes

The system must preserve accurate quantities, prices, and financial records when bookings change.

Rules for editing confirmed bookings, cancelling individual seed-type lines, and handling changes after procurement has been confirmed remain open.

## 7. Procurement Planning and Trips

### 7.1 Grouping bookings

- The owner groups bookings for procurement.
- The approximate vehicle capacity is 500 bags.
- The owner uses the accumulated quantities to determine when to arrange a trip.
- The application must calculate totals by seed type from the recorded bookings.
- The owner sends the supplier the required total quantity for each seed type.

The 500-bag figure is approximate. The application must not assume that every trip must contain exactly 500 bags.

### 7.2 Supplier coordination

The owner coordinates the trip with the supplier.

The system must record the planned quantities, relevant supplier, expected truck date, and actual trip details as these are finalized in the domain model.

A supplier-provided date can change. A planned trip can be cancelled.

The rules for assigning bookings to trips, splitting a booking across trips, or moving bookings between trips remain open.

### 7.3 Trip status

Trip state changes must be explicit and validated. A cancelled trip must not be treated as a successfully completed trip.

The final permitted status transitions and the required handling of associated bookings, advances, inventory, and supplier obligations must be specified before the trip workflow is implemented.

## 8. Actual Arrival and Accepted Quantities

### 8.1 Arrival recording

When the truck arrives, the owner records actual quantities received for each seed type.

Actual quantities can differ from planned quantities.

The system must preserve the distinction between:

- Planned quantity
- Physically received quantity
- Accepted quantity
- Rejected quantity
- Quantity subsequently delivered, wasted, or remaining

The final inventory model must prevent these categories from being confused or counted twice.

### 8.2 Quality inspection and rejection

- The owner inspects the arriving seed.
- Defective seed may be rejected immediately.
- The owner informs the supplier that rejected seed is not being purchased.
- Rejected quantities must be recorded and reflected in supplier settlement.

The system must retain the quantity, seed type, reason or notes, time of discovery, and associated trip where applicable.

The exact quality classifications and required evidence are open.

## 9. Shortages and Excess Seed

### 9.1 Shortages

When actual supply is less than planned demand:

- Record the shortage by seed type.
- Show the owner the affected quantities and bookings.
- Let the owner decide which customers receive the available quantity.
- Record the resulting allocation for each affected customer.
- Preserve the original booking and the decision history.

The application must not automatically distribute shortages proportionally or choose customers on the owner's behalf.

### 9.2 Excess quantities

When supply exceeds the expected requirement, the owner decides how the excess will be used.

Possible outcomes include:

- Selling additional quantities to existing customers who want more.
- Selling to unlisted or walk-in buyers at distribution spots.
- Retaining the quantity for the owner's pond.

The application must record the selected outcome and quantities so that remaining inventory and financial settlement can be reconciled.

The system must not automatically decide how excess seed is allocated.

## 10. Distribution Spots

The owner arranges distribution at a specified place, date, and time.

The application must support recording:

- Distribution spot details
- Relevant trip and bookings
- Customers who attend
- Quantity delivered to each listed customer
- Quantity originally booked versus quantity actually delivered
- Customer advances and remaining balances
- Payments collected
- Additional quantities sold
- Walk-in sales
- Defects or waste discovered at the spot
- Remaining quantities after distribution

The system must distinguish customers who do not attend, customers who receive partial quantities, and customers whose bookings are fulfilled, cancelled, or carried forward.

The exact attendance and no-show rules remain open.

## 11. Walk-in Buyers and Additional Sales

The owner may sell excess seed to buyers who did not make a prior booking.

For each walk-in sale, record at least:

- Buyer name
- Mobile number
- Seed type
- Quantity in bags
- Applicable selling rate and sale amount
- Payment information

The business may not have a complete customer profile for every walk-in buyer. Do not force every walk-in transaction to become a full customer account unless the owner approves that behavior.

The exact relationship between walk-in sales, customer records, inventory movements, and financial records must be defined in the architecture.

## 12. Customer Payments and Balances

### 12.1 Payment recording

The owner must be able to record customer payments.

Each payment must support:

- Amount
- Payment method or classification
- Relevant customer and transaction
- Payment date/time
- Any necessary reference or notes

The business distinguishes online payments from offline or cash payments.

The precise list of supported methods, partial-payment rules, and payment correction procedures remains open.

### 12.2 Customer balance

The system must track:

- Transaction amount
- Advance received
- Subsequent payments
- Amount still due
- Outstanding customer balances

Balances should be derived from reliable transaction and payment records, not maintained as an independently editable number without reconciliation.

The rules for overpayments, refunds, payment reversals, and credit balances remain open.

## 13. Defects, Waste, and Complaints

### 13.1 Defect discovery

Defective seed or waste may be identified:

- On arrival
- At a distribution spot
- During transit
- Later, following a customer complaint

The application must associate each recorded quantity with its seed type and relevant business event.

Where practical, it must record the discovery time, quantity, reason, source, and related trip or transaction.

### 13.2 Owner-controlled resolution

The owner decides how to resolve complaints and defects on a case-by-case basis.

Possible outcomes and compensation rules have not yet been fully specified. The system must record the chosen resolution rather than assume that every complaint results in the same refund, replacement, or deduction.

### 13.3 Supplier settlement impact

All waste and rejected quantities must be considered in supplier settlement, regardless of when the defect or waste is discovered.

However, the application must distinguish quantities already excluded from the supplier purchase from quantities whose supplier cost has already been accounted for. This is necessary to prevent double deductions.

The exact financial treatment of defects discovered after a completed supplier settlement remains open.

## 14. Trip Cancellation

A trip may be cancelled.

For each affected customer, the owner decides whether the advance should be:

- Refunded
- Carried forward to a future booking

The system must record the decision and resulting financial or credit state.

A cancellation must not automatically refund every customer or carry every advance forward.

The final cancellation workflow must define the effects on bookings, supplier orders, inventory, and any costs already incurred.

## 15. Supplier Settlement

### 15.1 Settlement calculation

The intended supplier bill is based on:

**Supplier bill = cost of accepted seed + vehicle charge − applicable deductions**

Where:

- Cost of accepted seed is calculated using the applicable buying rate for each seed type.
- Vehicle charge is recorded for the relevant trip.
- Applicable deductions include supplier advances and the agreed financial treatment of rejected or wasted seed.
- The final payable amount must reflect the documented settlement rules without double-counting rejected quantities, waste, or previous deductions.

The owner settles through the supplier's driver at the end of the trip.

### 15.2 Supplier payment records

The system must record:

- Supplier and associated trip
- Accepted quantities and buying rates
- Vehicle charge
- Supplier advance
- Applicable deductions
- Final calculated bill
- Amount paid during settlement
- Remaining payable or outstanding amount
- Settlement status and history

The calculation must be reproducible from the underlying records.

Rules for multiple supplier payments, partial settlement, corrections after settlement, and negative settlement balances remain open.

## 16. End-of-Trip Reporting

The application must help the owner reconcile the trip.

### 16.1 Money

Report:

- Online payment totals
- Offline or cash payment totals
- Customer amounts outstanding
- Supplier bill
- Supplier advances and deductions
- Supplier amount paid
- Supplier amount remaining payable

Reports must distinguish money collected from money merely due.

### 16.2 Quantities

For each seed type, report:

- Planned quantity
- Actual quantity received
- Accepted quantity
- Rejected quantity
- Quantity delivered to booked customers
- Additional and walk-in sales
- Waste and defects
- Quantity retained for the owner's pond
- Remaining quantity

The final inventory definitions must ensure these categories reconcile without overlap or double-counting.

### 16.3 Financial results

The system must support calculating financial results from recorded sales, buying costs, vehicle charges, deductions, payments, and other approved expenses.

The exact definition of profit, treatment of unsold seed, owner-pond transfers, and other expenses remains open. Do not label a figure as final profit until these rules are established.

## 17. Workflow and Auditability

Booking, trip, distribution, and supplier settlement must have explicit statuses and permitted transitions.

The system must preserve a useful history of important business decisions, quantities, rates, payments, and exception resolutions.

The detailed audit requirements—including which actions require an audit entry, whether deleted records are allowed, and how corrections are represented—remain open.

## 18. Data Integrity

The application must protect against:

- Delivering more quantity than is available without an explicitly recorded business decision.
- Treating rejected seed as accepted purchased stock.
- Losing the original booked quantity when a shortage occurs.
- Applying a new standard rate retroactively to historical transactions.
- Counting one quantity in multiple incompatible inventory categories.
- Applying the same advance or deduction twice.
- Recording settlement totals that cannot be reconciled with underlying transactions.
- Invalid workflow transitions.
- Saving only part of an operation that is required to succeed or fail atomically.

Database transactions and appropriate constraints must be used where required.

## 19. Initial Implementation Scope

The first vertical slice is limited to story-like generic record-engine learning using a placeholder `Request` record, followed by the first real business vertical slice: Product Master for fish seed types.

The generic engine learning slice is not a business requirement for the finished fish application.

The Product Master slice must eventually demonstrate:

- A record specification
- Validation
- Persistence
- API operations
- A React list and form
- Verified end-to-end behavior

Authentication is an early follow-up requirement. It must not be mistaken for permission to implement the entire application at once.

## 20. Open Business Decisions

Maintain these questions until the owner answers them:

1. Can a booking contain multiple seed types with different rates and quantities? (The current requirement says yes.)
2. What is the exact booking confirmation and cancellation process?
3. Can a booking be split across multiple trips?
4. What determines the larger-quantity pricing threshold?
5. How are standard and special selling rates prioritized?
6. What are the allowed trip and booking status transitions?
7. How are partial deliveries and undelivered quantities carried forward?
8. How are supplier-specific buying rates handled?
9. How are late customer complaints treated after supplier settlement?
10. What exact rules define profit and remaining inventory?
11. How are payments corrected, refunded, or reversed?
12. Can a customer owe money across multiple bookings?
13. How are customer advances linked to a cancelled or rescheduled booking?
14. What happens when seed is retained for the owner's pond?
15. Which business records may be edited, voided, or reversed after completion?
16. What audit history must be retained?

Do not treat this list as exhaustive. Add questions when implementation exposes missing rules.

## 21. Requirement Status

Each requirement should eventually be tracked as one of:

- `CONFIRMED`: Owner has approved the rule.
- `OPEN`: A decision is needed.
- `PLANNED`: Confirmed requirement scheduled for a future phase.
- `IN_PROGRESS`: Currently being implemented.
- `IMPLEMENTED`: Code exists.
- `VERIFIED`: Behavior has been tested against the requirement.
- `DEFERRED`: Explicitly postponed, with a reason.

Implementation status does not change whether the underlying business requirement exists.
