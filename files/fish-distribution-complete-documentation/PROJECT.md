# Fish Seed Distribution Management App

## 1. Project Purpose

Build a complete application to manage a fish seed distribution business, from customer booking through supplier procurement, seed arrival, distribution, payments, defect handling, and final financial settlement.

The application is intended to help the business owner record operations accurately, understand the current state of every trip and booking, track quantities and money, and maintain a reliable history of decisions.

This is a real business workflow, not merely a CRUD demonstration or a generic record-management application.

## 2. Product Owner and Users

The business owner is the primary and initially the only authenticated application user.

The following people are business participants, not application accounts by default:

- Customers
- Suppliers
- Drivers
- Unlisted or walk-in buyers

The owner records information about these participants and performs the business operations through the application.

Do not introduce customer, supplier, or driver login systems unless explicitly approved as a future requirement.

## 3. Technology Stack

### Current stack

- Backend: Python and FastAPI
- Dependency and project management: `uv`
- Frontend: React
- Database: Postgres

### Database evolution

PostgreSQL has not been selected for this project. The current decision is to use POstgres for learning and the initial implementation.

If the final deployment requirements justify PostgreSQL, document and evaluate that change before implementing it.

### Other technology decisions

Do not introduce additional frameworks, infrastructure, queues, or services without a documented reason tied to a requirement.

## 4. Architectural Direction

The project studies and adapts the reusable architecture patterns found in LeoSpark.

The intended backend design separates:

- Domain definitions and business concepts
- Declarative record specifications
- Reusable record operations
- Domain-specific business services and actions
- API routing and request/response contracts
- Persistence and database transactions
- Authentication, authorization, and application configuration

The frontend must use the backend API rather than bypassing business rules or directly modifying the database.

The final architecture must support the complete business application. The first implementation is a learning slice within that architecture, not the definition of the entire product.

See `ARCHITECTURE.md` for the target design.

## 5. Business Authority

The owner makes operational decisions.

The application records decisions, enforces confirmed business rules, performs calculations, and reports resulting states. It must not independently make business decisions that belong to the owner.

Examples include:

- Allocating shortages among customers
- Deciding how to handle excess seed
- Resolving customer complaints
- Deciding whether advances are refunded or carried forward after cancellation
- Deciding how to handle an individual customer's outstanding balance

The application may calculate quantities and amounts from recorded inputs, but it must not invent operational decisions.

## 6. Learning Method

The project is also a structured software-engineering learning exercise.

The learner must understand and implement the system incrementally rather than merely receive a finished codebase.

Use these principles:

1. Always have a plan.
2. Restate the problem.
3. Divide the problem.
4. Start with what is already known.
5. Reduce the problem.
6. Look for analogy.
7. Experiment.
8. Do not frustrate.

### Interaction rules

- Ask one design question at a time when a decision is required.
- Let the learner make business and architecture decisions.
- Explain the purpose and trade-offs before asking for a decision.
- Give hints and focused examples instead of automatically providing entire implementations.
- Let the learner implement the next step.
- Verify behavior before proceeding.
- Use actual command output, tests, and observed behavior as evidence.
- Do not silently decide unresolved requirements.
- Do not skip ahead to later phases.
- Keep explanations focused on the current learning objective.

## 7. Source of Truth

Use these files as the project's documentation:

- `PROJECT.md`: product context, constraints, and learning method.
- `REQUIREMENTS.md`: business rules and use cases.
- `ARCHITECTURE.md`: target technical architecture.
- `BUILD_PLAN.md`: implementation phases and dependencies.
- `CURRENT_TASK.md`: current progress and immediate task.
- `DECISIONS.md`: confirmed decisions and unresolved questions.

When documentation conflicts with code, do not assume either is correct. Identify the discrepancy and determine whether the code is outdated, the documentation is wrong, or a deliberate change has occurred.

## 8. Non-Negotiable Rules

- Do not invent business rules.
- Do not silently alter confirmed requirements.
- Do not confuse the learning engine with the final business domain.
- Do not mark unimplemented functionality as complete.
- Do not replace owner decisions with automatic allocation or resolution logic.
- Do not implement multiple unrelated learning objectives in one step.
- Do not claim a feature works without verification.
- Record architectural changes and their rationale in `DECISIONS.md`.
