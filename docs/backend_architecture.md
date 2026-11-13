# Backend architecture

Studyflow uses asynchronous FastAPI with PostgreSQL as its persistent store. [README](../README.md#local-setup) covers installation and environment setup.

## Layer boundaries

```text
Request -> Router/schema -> Service -> Repository -> PostgreSQL
Response <- Pydantic DTO <- Service <- query result
```

I chose explicit Controller -> Service -> Repository -> Data boundaries so HTTP behavior, application rules and SQL remain independently readable. FastAPI Depends wires the authenticated owner, async transaction and feature services.

```text
backend/
|-- app/
|   |-- main.py             # ASGI setup, middleware and lifecycle
|   |-- api/dependencies.py # Authentication and dependency wiring
|   |-- api/v1/             # Versioned controllers and router
|   |-- core/               # Config, security, errors and logging
|   |-- db/                 # Base, model registry, engine and session
|   |-- models/             # SQLAlchemy tables and record mixins
|   |-- schemas/            # Pydantic requests, responses and queries
|   |-- services/           # Business rules and orchestration
|   |-- repositories/       # Owner-scoped SQL and persistence
|   `-- tasks/resets.py     # Reset execution/recovery and session cleanup
|-- tests/                  # Guarded PostgreSQL integration, unit and performance tests
|-- .env.test.example       # Dedicated test database configuration
|-- alembic/env.py
|-- alembic/versions/
|-- alembic.ini
`-- pyproject.toml
```

| Responsibility | Service / repository |
| --- | --- |
| Courses, planner, notes, goals and restore | resources.py; shared CRUD with feature-specific rules |
| Authentication and profile | auth.py; password/token helpers in core/security.py |
| Timer transitions and history | timer.py |
| Preferences, trash, export, reminders | settings.py |
| Today/dashboard aggregation | dashboard.py |
| Reset acceptance and status | jobs.py; worker in tasks/resets.py |

Controllers and schemas have corresponding feature files. I extend shared behavior within its existing layer instead of adding wrapper-only modules.

## Data and transactions

The application tables are users, auth_session, course, study_session, note, goal, timer, focus_session, settings and job. Alembic also maintains its revision table.

- Accounts, focus records and jobs use UUIDs. Course/note/goal/planner IDs are positive JavaScript-safe numbers supplied by the current frontend.
- Owned records include user_id. Composite foreign keys enforce ownership/course consistency.
- courseId is authoritative; subject is a compatibility label synchronized from the course title.
- Database uniqueness constraints and service checks prevent duplicate active titles/study slots.
- Courses, notes, goals and planner sessions use deleted_at; normal reads exclude deleted rows.
- Repositories use parameterized SQLAlchemy expressions, async select/execute/scalars and modern mapped columns.

db/session.py provides the asyncpg engine, SessionLocal and get_db. Function-scoped dependencies commit successful work before the response and roll back failures. Owner locks serialize conflicting writes and guard reset/export. Pool size, overflow, recycle and timeouts are configurable.

## Authentication and authorization

I use Argon2 password hashes and random opaque cookie sessions rather than JWTs.

1. Signup requires at least 12 characters, lowercase, uppercase, a digit and supported punctuation.
2. Credential verification runs off the event loop.
3. Login creates a random token; PostgreSQL stores its SHA-256 digest and expiry.
4. The browser receives an HTTPOnly, SameSite=Lax cookie. Production configuration requires Secure cookies.
5. Protected queries include the current user's ID. Missing/foreign-owned resources have the same 404 response.
6. Logout revokes the session and clears the cookie.

The cookie is browser-session scoped; server validity is bounded separately by SESSION_MAX_AGE_SECONDS. The frontend's fresh-visit login rule is a UX policy, not an additional authorization boundary.

## API catalog

All paths are relative to **/api/v1**. Current OpenAPI inventory: **41 operations across 27 paths**. Controllers and schemas are authoritative.

| Area | Routes | Controller |
| --- | --- | --- |
| Account/session | POST /users; POST /sessions; GET/PATCH /users/me; DELETE /sessions/current | auth.py |
| Courses | GET/POST /courses; GET/PATCH/DELETE /courses/{id}; POST /courses/{id}/restore | courses.py |
| Planner | GET/POST /study-sessions; PATCH/DELETE /study-sessions/{id}; POST /study-sessions/{id}/restore | planner.py |
| Notes | GET/POST /notes; GET/PATCH/DELETE /notes/{id}; POST /notes/{id}/restore | notes.py |
| Goals | GET/POST /goals; GET/PATCH/DELETE /goals/{id}; POST /goals/{id}/restore | goals.py |
| Timer/history | GET/PATCH /timers/current; GET /focus-sessions; GET /focus-sessions/summary | timer.py, focus_sessions.py |
| Preferences/data | GET/PATCH /preferences; GET /deleted-resources; GET /reminders; GET /data-exports | settings.py |
| Dashboard | GET /dashboards/summary | dashboard.py |
| Reset jobs | POST /data-resets; GET /data-resets/current | jobs.py |
| Readiness | GET /health | health.py |

Planner uses list records rather than an unused GET-by-ID route. Course/goal lookups support selection, and note GET-by-ID supports conflict recovery.

### Contracts and errors

Normal JSON responses use:

```json
{"ok": true, "data": {}}
```

Errors use an optional details array:

```json
{"ok": false, "error": "Request validation failed.", "details": ["body.title: Field required"]}
```

| Status | Meaning |
| --- | --- |
| 200 | Read, update, restore or export |
| 201 | Resource/account/session creation |
| 202 | Reset accepted |
| 204 | Delete/logout; no JSON body |
| 401 / 403 | Authentication required / rejected origin |
| 404 | Missing or foreign-owned resource |
| 409 | Duplicate, stale version/revision, invalid relationship or reset conflict |
| 413 / 422 / 429 | Body too large / validation error / rate limit |
| 500 / 503 | Sanitized server error / unavailable dependency |

Health returns its readiness schema directly and may return 503. Export returns a JSON download, without the success envelope. Error handlers avoid exposing SQL or server tracebacks.

Requests/responses use separate Pydantic schemas. Partial updates use model_dump(exclude_unset=True); response_model_exclude_unset is a serialization option, not the update mechanism. DTO aliases are camelCase; query names include course_id, sort_by and time_zone.

### List queries

Lists return items, page, limit, total and total_pages. Default limit is **10**, maximum **100**, computed offset at most **10,000**. An empty collection has total_pages: 0.

Search, optional filters, validated sort fields, count, ordering, offset and limit execute in SQL. Text search uses bound ilike expressions. Capabilities vary by query schema; unsupported fields are rejected. Focus history has its own query contract; dashboard and capped reminder reads are purpose-specific summaries.

## Feature invariants

### Courses, planner and goals

I validate every relationship against the current user. A linked planner goal must belong to the session's course. Planner stores a calendar date and HH:mm time separately; changing timezone does not rewrite them. Undated legacy records do not appear in Today until scheduled.

Manual goal progress is independent of linked-session completion counts. Deleting a goal unlinks its sessions; restoring it does not recreate those links. Courses containing active study resources or a running timer cannot be deleted.

### Notes

Note PATCH requires expectedVersion plus a non-null change. Content must contain text and is capped at 100,000 characters. The service checks versions under the owner lock; stale edits return 409. Updates, deletion and restore maintain version consistency. Responses expose version and updatedAt for the editor.

### Timer and history

Timer PATCH requires expectedRevision and a timer change object. The server owns deadlines, revisions, completion counts and focus timestamps.

- Configured bounds: focus 1-120 minutes, short break 1-30, long break 1-60.
- Fresh blocks/resets/mode changes use preferences. blockDuration preserves running/paused work when preferences change.
- Pause closes an interval; resume creates another. Partial focus time remains recorded.
- Breaks do not create focus-history records.
- Server-clock expiry completes each interval/count once; the display remains 00:00 until the next action.
- Weekly boundaries use the selected timezone and Monday/Sunday start. SQL aggregates days and the top 20 courses. Legacy counters do not fabricate intervals.

### Preferences and data controls

Theme retains its original column; other validated preferences use JSONB. SettingsService reuses a request-local snapshot, without cross-request caching.

Reminders query unfinished active sessions/goals in an indexed date window using the saved timezone. Goals use 09:00 on their deadline. The feed applies lead time, a one-minute grace and a cap of 100 candidates. Delivery requires the frontend to remain open; there is no email/closed-site push service.

Recently deleted uses a bounded SQL union over the four soft-deleted resource types. Restore reuses the existing services, including duplicate and parent validation.

Export holds the owner lock, reads bounded batches and prepares a temporary JSON file with file I/O off the event loop. Database work completes before headers; downloads read 64 KiB chunks and close the file. Deleted study records/preferences are included, credentials/auth sessions excluded. Import is not implemented; the proxy timeout remains 30 seconds.

Reset persists an owned job, returns its status/polling location and dispatches native background work. The worker atomically deletes timer, focus history, planner, notes, goals and courses while retaining the account, preferences and job status. Recovery processes queued jobs; this is not an external queue.

## Configuration and operations

core/config.py loads .env, or .env.production when APP_ENV=production is set in the process environment. Environment variables override files. Local values are in [README](../README.md#local-setup).

- CORS has explicit origins/methods/headers with credentials enabled.
- Middleware enforces request-size bounds, trusted hosts, write-origin checks, request IDs and response security headers.
- Production config validates HTTPS origins, Secure cookies and a __Host- cookie name; this is not a complete deployment audit.
- SlowAPI limits use per-process memory and reset on restart.
- Logging has a bounded queue, production JSON formatting and sensitive-data filtering; request bodies/cookies are not intentionally logged.
- Health checks PostgreSQL readiness; it is not a metrics platform.

## Migrations and maintenance

Current head: **0011**.

| Revision | Responsibility |
| --- | --- |
| 0001 | Accounts and sessions |
| 0002-0006 | Planner, notes, goals, timer and preferences |
| 0007 | Reset jobs |
| 0008 | Planner dates |
| 0009 | Courses and owned relationships |
| 0010 | Note versions and focus history |
| 0011 | Workspace preferences, block duration, extended focus bounds and trash indexes |

db/base.py imports all models for Alembic metadata; alembic/env.py uses an async connection. I group coherent schema changes into forward revisions and preserve applied history. Editing an old revision does not update a database stamped past it. I do not stamp head to bypass missing schema changes. The 0011 downgrade refuses incompatible longer focus records.

Run the README checks after changes. I maintain pytest unit tests and real PostgreSQL API, authentication, migration and performance checks in `backend/tests`. The [testing guide](testing-guide.md) records setup, safeguards, coverage and measured results. Deployment automation, shared rate-limit storage, external workers and closed-site notifications remain separate future work.
