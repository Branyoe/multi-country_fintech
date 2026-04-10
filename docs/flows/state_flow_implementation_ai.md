# State Flow Implementation Guide (AI-Oriented)

## 1. Objective

This document describes the implemented, state-driven workflow engine for credit applications.

The backend now enforces a deterministic execution model:

```
STATE (DB)
  -> update_status()
  -> workflow.on_enter()
  -> async task
  -> update_status()
  -> NEXT STATE
```

Key properties:
- orchestration is state-driven, not task-driven
- transition rules are fully DB-driven
- MX and CO use symmetric async pipelines
- technical failures are explicit (`technical_error`)
- all transitions are audited with metadata

## 2. Core Invariants

These invariants are enforced in code and tests:

1. All status mutations go through `CreditApplicationService.update_status()`.
2. Allowed transitions are validated against `StatusTransition` rows.
3. Terminal states are immutable.
4. `ApplicationStatusHistory` is written on every transition with metadata.
5. Every Celery task has idempotency guard by expected current state.
6. Retry exhaustion transitions to `technical_error`.

## 3. Domain Model

### 3.1 Country flow model
Source: `backend/countries/models.py`

- `Country`: metadata + document regex
- `CountryStatus`: country-scoped state node
- `StatusTransition`: directed edge (`from_status` -> `to_status`), same-country enforced
- `CountryValidation`: per-rule validation evidence

### 3.2 Application model
Source: `backend/applications/models.py`

- `CreditApplication`: stores current FK state (`status`)
- `BankProviderData`: provider snapshot persisted before validation step
- `ApplicationStatusHistory`: immutable audit log (`from_status`, `to_status`, `changed_by`, `metadata`)

## 4. Workflow Layer

Source folder: `backend/applications/workflows/`

Files:
- `base.py`
- `registry.py`
- `mx.py`
- `co.py`

### 4.1 Contract (`BaseWorkflow`)

- `get_country_code()`
- `on_enter(state_code, application)`
- `validate(application, bank_data)`

`on_enter` triggers side effects only. It must not mutate status directly.

### 4.2 Registry

`registry.py` lazily bootstraps country workflows and resolves by country code:

- `register(workflow_cls)`
- `get_workflow(country_code)`

## 5. Service Layer Semantics

Source: `backend/applications/services.py`

### 5.1 `create(data, user)`

Flow:
1. validate country + document format
2. resolve country initial status (`is_initial=True`)
3. create application in initial state
4. write initial history (`'' -> initial_status`)
5. bootstrap processing with transition to `fetching_bank_data` via `update_status()`

No task is manually dispatched from `create()`.

### 5.2 `update_status(application_id, new_status_code, changed_by, metadata=None)`

Flow:
1. load application
2. reject transition from terminal states
3. resolve target state by country
4. validate edge in `StatusTransition`
5. persist new status
6. append `ApplicationStatusHistory`
7. resolve workflow by `application.country`
8. call `workflow.on_enter(new_status.code, application)`

This is now the single orchestration entrypoint.

## 6. Task Layer

Source: `backend/applications/tasks.py`

Implemented task set:
- `fetching_bank_data_task`
- `validate_country_rules_task`
- `notify_final_decision_task`

Removed legacy tasks:
- `created_task`
- `process_application_mx`
- `consulta_buro_co`

### 6.1 Standard task template

Each task follows:
- load app
- idempotency guard (`if app.status_code != EXPECTED: return`)
- execute work
- transition using `update_status()` with metadata
- on exception: retry until max, then `technical_error`

### 6.2 Data persistence rules

- Bank data is persisted before transition from `fetching_bank_data`.
- Rule validations are persisted before transition from `validate_country_rules`.

## 7. Country Pipelines

### 7.1 MX pipeline

`created -> fetching_bank_data -> validate_country_rules -> approved|rejected`

Also allowed:
- `created -> technical_error`
- `fetching_bank_data -> technical_error`
- `validate_country_rules -> technical_error`

### 7.2 CO pipeline

`pending -> fetching_bank_data -> validate_country_rules -> approved|rejected`

Also allowed:
- `pending -> technical_error`
- `fetching_bank_data -> technical_error`
- `validate_country_rules -> technical_error`

MX and CO now share the same async decomposition and task behavior.

## 8. Fixture Graph

Source: `backend/fixtures/statuses.json`

- MX initial state: `created`
- CO initial state: `pending`
- both countries include:
  - `fetching_bank_data`
  - `validate_country_rules`
  - `approved`
  - `rejected`
  - `technical_error`

Transition matrix remains fully data-driven from fixtures / DB.

## 9. Error Model

Business vs technical outcomes are separated:

- business rule failure -> `rejected`
- technical failure after retries -> `technical_error`

No silent failures:
- every task failure either retries or transitions to `technical_error`

## 10. Testing Coverage

Source: `backend/applications/tests/test_applications.py`

Validated behaviors:
- workflow triggers proper `.delay()` call on state enter
- idempotency guards (task no-op when state mismatches)
- retry exhaustion to `technical_error`
- full async pipeline for MX and CO
- transition validation and terminal immutability
- history metadata persistence

Run commands:

```bash
cd backend && uv run pytest applications/tests/test_applications.py -q
cd backend && uv run pytest -q
```

Current result after refactor:
- `applications/tests/test_applications.py`: 49 passed
- full backend suite: 62 passed

## 11. Extension Playbook (new country)

To add a new country workflow safely:

1. add country + states + transitions in fixtures
2. add validator and register it
3. implement workflow file in `applications/workflows/`
4. map `on_enter` to shared task set
5. ensure transitions to `technical_error` exist for technical failure points
6. add tests for pipeline success + rejection + retry exhaustion

## 12. Operational Notes

- Workflow lookup failure raises explicit error (`Workflow no registrado para país`).
- Because orchestration happens in `update_status()`, manual PATCH transitions can trigger async effects by design.
- Tests patch Celery `.delay()` to avoid accidental async execution during API tests.
