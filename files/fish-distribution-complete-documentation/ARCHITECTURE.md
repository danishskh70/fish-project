# Target Architecture — Fish Seed Distribution Management App

## 1. Purpose

Define the intended architecture for the complete application.

This is the target design. It is not a statement that every component already exists or that every technical decision is finalized.

The architecture must support both:

1. Reusable record-management capabilities for ordinary business entities.
2. Explicit business workflows that require domain rules, decisions, calculations, and state transitions.

The generic engine must not become a universal mechanism that hides or replaces business logic.

## 2. Architectural Principles

### 2.1 Separation of responsibilities

Each component should have a clear responsibility.

- API routers handle HTTP boundaries.
- Schemas define input and output contracts.
- Authentication identifies the user.
- Authorization determines whether the user may perform an operation.
- Specifications describe supported generic record behavior.
- The record engine implements reusable record operations.
- Domain services implement business operations.
- Persistence components manage database access and transactions.
- Workflow rules control valid state transitions.
- React presents information and collects user input.

### 2.2 Explicit business behavior

Business rules must be expressed in identifiable, testable functions or services.

Do not hide important behavior inside generic CRUD handlers, frontend components, model constructors, or scattered conditional expressions.

### 2.3 Reuse without over-generalization

Reuse stable patterns that occur across multiple record types.

Do not build an abstraction solely because a future feature might need it.

### 2.4 Traceability

Important operations must be traceable from the API entry point through authorization, validation, business logic, persistence, and response.

### 2.5 Incremental implementation

The target architecture is designed for the complete product. Implementation must proceed in small, verified vertical slices.

## 3. High-Level System

The application has a React frontend, a FastAPI backend, and a relational database.

The frontend communicates with the backend through defined HTTP APIs.

The backend authenticates requests, validates inputs, authorizes operations, executes domain logic, persists changes, and returns structured responses.

The database stores business entities, transaction records, workflow states, and relevant history.

Do not allow the frontend to bypass backend business rules.

## 4. Backend Layers

### 4.1 Application entry point

Responsibilities:

- Create the FastAPI application.
- Load application configuration.
- Register API routers.
- Configure middleware and exception handling.
- Initialize and close resources where necessary.

The entry point should compose the application, not contain individual business workflows.

### 4.2 API routers

Responsibilities:

- Define HTTP endpoints.
- Declare request and response schemas.
- Apply authentication and authorization dependencies.
- Invoke the appropriate record or domain service.
- Return appropriate HTTP responses.

Routers must not become the primary location for business rules or database queries.

### 4.3 Authentication and authorization

Responsibilities:

- Authenticate the owner using the chosen authentication mechanism.
- Validate Bearer JWT credentials.
- Identify the authenticated principal.
- Enforce the permissions required by each operation.

Authentication and authorization are separate concerns.

The current application initially has one owner account. The initial WRITER-role learning requirement must be reconciled with the final owner-only model before authentication is finalized.

### 4.4 Schemas

Schemas define external input and output contracts.

They must validate incoming data and shape API responses.

A schema is not automatically a database model, a business entity, or a record specification. These concepts may share field names without sharing responsibilities.

### 4.5 Record specifications

A `Field` describes metadata about a supported field, such as its name, type, label, required status, and applicable validation or presentation information.

A `RecordSpec` describes the generic behavior and metadata of one supported record type.

The exact fields, validation strategy, serialization format, and extension points are to be designed during the learning phase.

A specification must not become an unrestricted container for arbitrary business logic.

### 4.6 Generic record engine

The record engine provides reusable operations for record types whose behavior fits the common record model.

Expected capabilities may include:

- Listing records
- Retrieving a record
- Creating a record
- Updating an allowed record
- Deleting or deactivating a record where permitted
- Applying specification-driven validation
- Enforcing access and ownership constraints
- Producing consistent responses

These capabilities must be introduced only after their behavior and authorization rules are defined.

Not every business object should support every generic operation. For example, completed payments and settlements may need reversal workflows rather than ordinary deletion.

### 4.7 Domain services

Domain services implement business-specific operations.

Examples include:

- Confirming a booking
- Planning a procurement trip
- Recording actual arrival quantities
- Recording a shortage allocation
- Recording a delivery
- Recording a defect
- Calculating a supplier settlement
- Completing a trip

These operations coordinate validation, state changes, calculations, persistence, and transaction boundaries.

They must preserve owner-controlled decisions.

### 4.8 Persistence

Persistence components manage database interaction.

Responsibilities include:

- Querying and storing records
- Defining relationships
- Applying database constraints
- Managing transaction boundaries
- Supporting efficient data retrieval

The project must choose a consistent persistence approach before introducing a large number of models and services.

A separate repository layer is not mandatory merely for architectural appearance. Its value must be evaluated against the actual data-access complexity.

## 5. Target Reusable Pattern

The intended reusable pattern is:

`RecordSpec → RecordService → Router Factory`

The exact implementation may use factories, dependency injection, or other composition techniques where justified.

### RecordSpec

Defines the metadata and generic capabilities of a record type.

### RecordService

Implements the common record operations using the specification and persistence layer.

### Router factory

Creates consistent API endpoints for record types that fit the generic model.

This pattern must be tested with more than one record type before being considered genuinely reusable.

## 6. Generic Records Versus Domain Workflows

The generic record engine and business workflow services are complementary.

### Suitable candidates for generic record operations

- Fish seed type master
- Customer master
- Supplier master, if the final model requires it
- Other simple reference data

### Candidates requiring domain-specific behavior

- Bookings
- Procurement trips
- Quantity allocation
- Deliveries
- Customer payments
- Defect and waste handling
- Supplier settlements

A domain entity may still use common record metadata or shared persistence utilities. That does not mean all of its behavior should be implemented by generic CRUD.

The final classification must be confirmed as the domain model is designed.

## 7. Business Domain Boundaries

The target domain is organized around the following conceptual areas.

### Reference data

- Fish seed types
- Customers
- Suppliers
- Distribution locations, if required
- Pricing configuration

### Booking

- Customer booking
- Booked seed-type lines
- Applicable rates
- Advances and payment associations
- Booking state and history

### Procurement

- Trip planning
- Supplier orders or planned quantities
- Expected dates
- Actual arrival
- Accepted and rejected quantities
- Vehicle charges
- Supplier advances

### Inventory and distribution

- Accepted quantities
- Allocation decisions
- Distribution spots
- Customer deliveries
- Additional sales
- Walk-in sales
- Waste, defects, and remaining quantities
- Transfers to the owner's pond

### Finance

- Customer payment records
- Customer balances
- Supplier settlement calculations
- Supplier payments and balances
- Approved deductions
- Reconciliation and reports

These are conceptual boundaries, not a finalized database schema. Exact entities, relationships, and ownership must be designed and documented before their implementation.

## 8. Data Model Principles

- Represent distinct business concepts explicitly.
- Use stable identifiers for persistent records.
- Define relationships and their cardinalities intentionally.
- Preserve historical prices and transaction quantities.
- Avoid duplicating authoritative data without a clear reason.
- Use explicit transaction records for money movements.
- Distinguish planned, received, accepted, rejected, delivered, wasted, and remaining quantities.
- Prevent double-counting of inventory and financial deductions.
- Use constraints to protect data integrity.
- Model corrections in a way that preserves relevant history.

The exact database tables, foreign keys, uniqueness rules, indexes, and delete behavior remain to be finalized.

## 9. Transactions and Concurrency

Operations that must succeed or fail together must use a database transaction.

Examples include recording an accepted arrival quantity alongside its inventory movement, or completing a settlement alongside its payment records.

The application must prevent partial persistence when an operation fails.

Concurrency controls should be introduced where concurrent requests could cause incorrect quantities, duplicate payments, or inconsistent workflow transitions.

The specific locking or optimistic-concurrency strategy remains open.

## 10. Workflow Architecture

Workflow transitions must be explicit.

A workflow operation should:

1. Load the relevant records.
2. Validate the current state.
3. Validate required inputs.
4. Check authorization.
5. Apply business rules.
6. Persist all required changes atomically.
7. Record important decisions and changes.
8. Return the resulting state.

The exact sequence of validation and authorization may vary by operation, but security and integrity checks must never be bypassed.

Valid states and transitions must be defined for bookings, trips, distribution, payments, and supplier settlement before those workflows are implemented.

## 11. Error Handling

The backend must distinguish relevant failure categories, including:

- Invalid input
- Missing records
- Unauthorized requests
- Forbidden operations
- Invalid workflow transitions
- Conflicting updates
- Insufficient available quantity
- Database or unexpected internal errors

The API must return consistent, useful error responses without leaking credentials, secrets, or internal stack traces.

The precise error response schema remains to be defined.

## 12. React Frontend

The frontend must separate:

- Pages and layouts
- Reusable presentation components
- API communication
- Form state and client-side validation
- Authentication state
- Domain-specific user workflows

The frontend may improve usability with early validation, but the backend remains authoritative for business rules.

The target UI must support the owner's real operational workflow rather than expose only a list of database tables.

Generic record screens can be reused for suitable master data. Business workflows may require dedicated screens and actions.

## 13. Testing Strategy

The project must verify behavior at several levels.

### Unit tests

Test validation rules, calculations, and domain decisions.

### API tests

Test HTTP contracts, authentication, authorization, error responses, and persistence behavior.

### Transaction and integrity tests

Verify that operations roll back correctly and cannot leave inconsistent data.

### Integration tests

Verify the interaction among routers, services, and the database.

### Frontend and end-to-end tests

Verify important user journeys through the React UI and FastAPI API.

High-risk calculations and workflow transitions must have explicit tests.

## 14. Security

- Require authentication for protected operations.
- Enforce authorization on the backend.
- Never trust an owner identifier supplied by the client when it should come from authenticated identity.
- Validate external input.
- Store credentials and secrets securely.
- Do not expose secrets in logs or API responses.
- Use safe database operations.
- Restrict destructive operations and preserve financial history.
- Apply production deployment protections before exposing the service publicly.

## 15. Observability and Audit History

The application should provide enough logging to diagnose failures and understand important operational events.

Logs must not expose sensitive credentials.

Business audit history and technical logs serve different purposes. Financial changes and important owner decisions may require durable audit records beyond ordinary application logs.

The final audit schema, retention policy, and reporting needs remain open.

## 16. Deployment Architecture

Development currently uses a local FastAPI server and local React development tooling.

Production deployment details have not yet been finalized.

Before deployment, decide and document:

- Hosting environment
- Database location and backup strategy
- Application process management
- Frontend serving
- HTTPS and reverse proxy configuration
- Secret management
- Database migrations
- Logging and monitoring
- Recovery procedures

Do not treat local development configuration as a production deployment plan.

## 17. Architectural Decision Rules

Before introducing a new abstraction:

1. Identify the concrete problem it solves.
2. Identify which existing components are insufficient.
3. Compare simpler alternatives.
4. Consider the cost of maintaining the abstraction.
5. Record the decision in `DECISIONS.md`.

Before changing the target architecture:

1. Identify the requirement or evidence that motivates the change.
2. Identify affected components and workflows.
3. Consider migration and compatibility effects.
4. Update the documentation.
5. Implement and verify the change in a controlled step.

## 18. Architecture Status

The overall separation between reusable record operations and domain-specific workflows is the intended direction.

The exact database schema, persistence implementation, transaction strategy, error contract, frontend organization, and production deployment are not all finalized.

Do not claim these details are confirmed until they have been decided and recorded.
