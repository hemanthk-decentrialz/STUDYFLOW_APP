# Studyflow testing guide

I use automated backend tests to protect the same cookie-authenticated workflows my Next.js frontend calls. I test against real PostgreSQL because SQLite would miss PostgreSQL constraints, partial indexes, JSONB, asyncpg behavior and migration problems. These checks are a development regression suite, not a production load or penetration test.

## Tool choices and file map

| File/tool | What I use it for | Why |
| --- | --- | --- |
| `backend/pyproject.toml` | pytest, pytest-asyncio, HTTPX dev dependencies and strict markers | One existing dependency/configuration source |
| `backend/tests/conftest.py` | Isolated configuration, migration setup, async clients and cleanup | Consistent setup without connecting tests to my development database |
| `backend/tests/support.py` | Database safety guard and cookie-aware API helpers | Shared test behavior has one owner |
| `backend/tests/test_unit.py` | Validation, pagination bounds, service conflicts, logging privacy, hashing thread handoff, rate limits, sanitized errors and TestClient smoke | Small checks isolate rules without a database |
| `backend/tests/test_auth_api.py` | Real signup/login/logout, expiry, cookie storage, protected routes, CORS, ownership, concurrency and DB rollback | Authentication needs actual persistence and independent client cookie jars |
| `backend/tests/test_resources_api.py` | Courses, notes, goals and planner CRUD, links, duplicates, note conflicts, restore and database-side listing | These are my frontend resource contracts |
| `backend/tests/test_focus_settings_api.py` | Timer authority/completion, preferences, history, summaries, reminders, exports, reset jobs, lifecycle and Alembic drift | Cover behavior that spans several layers |
| `backend/tests/test_performance.py` | Seeded PostgreSQL plans, SQL statement counts and connection reuse | Measure the actual repositories rather than assume they are efficient |
| `docs/postman/` | Importable collection and local environment | Repeatable manual request workflow without another application dependency |
| Swagger `/api/v1/docs` | Interactive schema/request inspection | The API generates its own current contract |

I chose HTTPX `AsyncClient` with `ASGITransport` for database-backed API tests. The client, application and asyncpg engine share one session-scoped asyncio loop. I use FastAPI's synchronous `TestClient` only for a database-free smoke check; sharing an asyncpg pool across its separate thread/loop is unsuitable here. HTTPX transport does not automatically start lifespan: one dedicated test enters the real application lifespan, while normal tests avoid concurrent recovery-worker interference. See [FastAPI async testing](https://fastapi.tiangolo.com/advanced/async-tests/) and [HTTPX ASGI transport](https://www.python-httpx.org/advanced/transports/#asgi-transport).

## Set up a separate test database

**Tests migrate and clear every application table in the selected test database before and after each database test. Never put real data there.** Alembic's version table remains intact between tests. I keep development, production and test credentials separate and do not commit `.env.test`.

From PowerShell in the project directory:

```powershell
cd backend
# Use my existing environment, or create one with an installed supported Python:
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
if (-not (Test-Path -LiteralPath .env.test)) {
    Copy-Item .env.test.example .env.test
}
```

I can use another installed Python version supported by `requires-python` if 3.14 is unavailable. Calling the environment's interpreter directly avoids activation-policy problems. If `.venv` already works, I skip recreating it.

Connect as my local PostgreSQL administrator using pgAdmin Query Tool or `psql` and run the two statements separately, outside an explicit transaction:

```sql
CREATE ROLE studyflow_test LOGIN PASSWORD 'CHOOSE_A_UNIQUE_LOCAL_TEST_PASSWORD';
CREATE DATABASE studyflow_test OWNER studyflow_test;
```

In `backend/.env.test`, I replace the example with my real **test-only** password:

```dotenv
TEST_DATABASE_URL=postgresql+asyncpg://studyflow_test:URL_ENCODED_TEST_PASSWORD@127.0.0.1:5432/studyflow_test
```

I URL-encode reserved characters in the password. I do not change `backend/.env` or any frontend environment variable for this suite. Alternatively, I set `$env:TEST_DATABASE_URL` for the current terminal; it takes precedence over `.env.test`.

My safety checks require the asyncpg URL, an explicit host, a database ending in `_test`, no URL query overrides, and a different host/port/database target from `DATABASE_URL`. They treat `localhost`, `127.0.0.1` and `::1` as the same local host and reject `APP_ENV=production`. Before truncation, the fixture checks PostgreSQL's actual database name. A PostgreSQL advisory lock rejects concurrent test suites against the same test database. These checks supplement dedicated least-privilege credentials; they cannot detect every custom DNS alias or deliberately incorrect environment configuration.

## Run the suite

Run these commands from `backend`:

```powershell
# No database required:
.\.venv\Scripts\python.exe -m pytest tests -m unit -q

# Full run: missing test DB configuration is an error, not a silent skip:
.\.venv\Scripts\python.exe -m pytest tests --require-db -q

# Reproduce measured PostgreSQL evidence:
.\.venv\Scripts\python.exe -m pytest tests -m performance --require-db --performance-report .test-artifacts/performance.json -q

# Lint all application and test code:
.\.venv\Scripts\python.exe -m ruff check app tests
```

Without `--require-db`, database tests skip when no test database is configured. I use `--require-db` for a complete verification. I run from `backend` and pass `tests` explicitly so pytest discovers the custom database/report options before parsing them and Alembic finds its configuration. I do not use pytest-xdist against one database. Assertions never rely on test order or data left by a previous test. Setup applies existing migrations through head; the integration suite also runs `alembic check` against the migrated schema.

The suite raises ordinary API rate limits only inside its test process to avoid one scenario exhausting another's budget. A separate isolated test verifies a real low limit returns HTTP 429 and `Retry-After`. Authentication uses actual Argon2 hashes and actual session rows; only the utility handoff unit test substitutes the hasher to check its execution thread.

## Scenarios and expected behavior

| Scenario | Expected result |
| --- | --- |
| Valid signup/resource creation | 201; validated response without credentials |
| Valid reads, partial PATCH and restore | 200; omitted fields preserved |
| Delete/logout | 204 with an empty body |
| Queued reset | 202, then owned job status; completed reset preserves account/preferences |
| Missing fields, invalid input, unknown query fields, excessive page size/offset | 422 and the frontend error envelope |
| Duplicate email/title/slot or stale note/timer revision | 409; rejected changes do not overwrite data |
| Missing/expired session | 401 and cleared cookie |
| Untrusted write Origin | 403 |
| Missing/deleted/another user's resource | 404; ownership is deliberately not disclosed |
| Rate limit exceeded | 429 with retry guidance |
| Unexpected exception | Generic 500 without internal exception details |

I verify relation ownership as well as resource ownership: a note needs an active owned course, a planner session's goal must belong to that course, and a nonempty course cannot be removed. Soft-deleted records disappear from normal lists, appear in the owned trash and can be restored unless their parent or unique title conflicts. Deleting a goal unlinks planner sessions. Note versions protect edits, deletion and restoration from stale drafts.

Timer tests move persisted timestamps rather than sleep through a Pomodoro. I verify one completion is counted once, clients cannot forge completion counters or shorten a new interval to earn study time, stale revisions fail, and breaks produce no focus records. Export tests verify line breaks/indentation, valid JSON, included deleted study data and excluded credentials/sessions. The focused settings/timer/export suite passed all 13 tests after this formatting change. Reset tests execute native BackgroundTasks through the ASGI response and verify another account remains intact.

## Manual website acceptance checklist

I start PostgreSQL and both development servers using the README, then open `http://localhost:3000`. I use disposable accounts for this checklist and a second browser profile for permission checks. I inspect the browser Network and Console panels as well as the visible UI; a successful click alone does not prove data was saved.

| Area | What I do | What I expect |
| --- | --- | --- |
| Account access | Sign up with a weak password, then valid credentials; try a wrong password and then sign in correctly | Clear validation/errors; successful login opens Today; no password appears in response data |
| Session behavior | Refresh an authenticated tab, then open the website in a new tab without its session marker | Refresh preserves verified access and the current route; a new tab without a marker asks for login. A temporary verification outage offers retry; logout/401 clears access |
| Courses | Create PostgreSQL and Python courses; edit a title; attempt a duplicate | Saved changes survive refresh; linked resource labels follow renames; duplicate names are rejected |
| Course picker | Select a course, search by part of its name, use arrows/Enter/Escape | One searchable picker; a saved relationship requires a real course selection |
| Planner | Add a dated session for today, complete it, edit its date/time and link an appropriate goal | Today and planner agree; completion persists; a goal from another course is rejected |
| Notes | Create a note, edit it and wait for Saved; reload; then change the same note from two separate signed-in contexts | Content persists; stale versions produce a recovery choice rather than silently overwriting. In a fresh second tab I sign in again as required by the visit policy |
| Draft recovery | Type unsaved content, navigate/reopen the editor and review its recovered draft | Local text remains recoverable; I review recovered content before autosave resumes |
| Goals | Create a deadline, change progress to 0/40/70/100, and complete a linked planner session | Progress persists and colours remain consistent; manual progress and linked-session counts remain separate |
| Filters and pagination | Create 11 notes; open Filters, search/sort/filter, then move between pages | Filters disclose beside the title; default page size is 10; page 2 contains the remaining item; one-page results hide pagination |
| Focus | In Settings set focus to one minute; start, pause, resume and wait for completion; try a break | The timer reconciles server state, ends at 00:00 and counts completion once; focus intervals appear in history, while breaks do not |
| Preferences | Change durations, time zone, week start, time format, sound and theme; navigate/reload | Preferences persist; running/paused blocks retain their original duration; fresh blocks use new preferences |
| Reminders | Enable session reminders and create a session within the lead-time window | An open app shows one reminder for the due item; device notifications need browser permission and sound may need a user gesture |
| Profile/navigation | Update my display name, open Profile from header/sidebar, collapse desktop navigation and use the mobile drawer | Name changes persist; each navigation action works; keyboard Escape closes the drawer |
| Delete/restore | Delete a note, use Undo, delete again and restore from Settings > Recently deleted | The record is removed from normal lists and actually restored by the backend; conflicting titles/parents show an actionable error |
| Export | Download JSON and inspect it locally | The download icon has an accessible label; the file is indented JSON containing my study data, preferences and deleted records, without passwords or auth sessions |
| Reset | Only in a disposable account, confirm Reset Application and wait for completion | Study data/history is permanently cleared; account and preferences remain; another account is unaffected |
| Logout/permissions | Log out and try a protected API; in another browser profile log in as another account and request an owned resource ID | Logged-out API returns 401; foreign resources return 404 and cannot be modified or deleted |
| Failure recovery | Stop the backend, attempt a read/save, restart it and retry | Useful error/pending feedback; unsaved text is retained; retry recovers without a false Saved message |
| Layout/accessibility | Repeat key flows in sunwashed-peach light/phosphor-terminal dark themes and narrow/wide layouts; navigate using Tab | Canvas, cards, pickers, loaders and reset feedback share the palette; hover/focus and success/warning/error states stay readable |
| First visit | Open localhost:3000 in a new tab without a session marker | Redirect to login without dashboard-specific copy; slower startup says Loading Studyflow, while a fast redirect avoids flashing loader contents |

For each failed case, I record the page, steps, expected/actual result and HTTP status without attaching passwords, cookies or private exports. I do not mark manual acceptance complete until I have actually performed the checks. Automated backend tests do not certify every browser interaction.

## Swagger: one complete manual example

1. Start my backend using the README instructions with `DOCS_ENABLED=true`, then open `http://localhost:8000/api/v1/docs`. Keep the hostname consistent throughout.
2. Execute `POST /api/v1/users` with a disposable name, email and a password of at least 12 characters including upper/lowercase, a digit and punctuation.
3. Execute `POST /api/v1/sessions` using that email/password. The browser stores the HttpOnly session cookie. I do not paste a JWT into Authorize: this app uses cookie sessions.
4. Execute `GET /api/v1/users/me`; expect 200. Swagger sends the cookie automatically on the same origin.
5. Create a course, then a note with matching `courseId`:

```json
{"id":9001,"title":"PostgreSQL","description":"Database study"}
```

```json
{"id":9002,"courseId":9001,"title":"Joins","content":"Inner and outer joins"}
```

6. Read `/notes` using `search=joins`, `course_id=9001`, `sort_by=title`, `order=asc`, `page=1`, `limit=10`. Query filters use the names Swagger shows; JSON response fields use the existing frontend aliases such as `courseId`.
7. PATCH `/notes/9002` using `{"expectedVersion":1,"content":"Revised notes"}`. Repeat with version 1 to see 409; read the note again before retrying with its latest version.
8. Delete the note (204), verify its active read is 404, then POST its `/restore` route (200).
9. DELETE `/sessions/current`, then GET `/users/me` to see 401.

I inspect response bodies, status codes, cookies and request headers, not just the green Swagger response label. For ownership, I use two independent browser profiles or Postman cookie jars. A 404 for someone else's resource is the intended permission response. CORS is browser enforcement; automated preflight and Origin-policy tests complement these manual checks.

## Postman collection and environments

I import `docs/postman/studyflow.collection.json` and `local.environment.json`, select that environment, fill `email` with a new disposable account and enter a strong `password` locally. `base_url` defaults to `http://localhost:8000`. I never export my populated password or cookies.

I run requests in numbered order. The cookie jar retains the login session; Authorization remains **No Auth**, with no Bearer header. The collection validates each expected HTTP status, exercises request bodies/query variables, saves the timer revision and demonstrates stale updates, duplicates, invalid pagination, soft deletion and logout. The example numeric IDs/titles must be unused; to repeat, I use a fresh account. The timer request starts a real interval in that disposable account. Reset operations are excluded from the default manual collection to avoid accidentally erasing study data. Swagger documents all routes; the collection is a representative workflow, not a second OpenAPI specification. I chose Postman rather than maintain an overlapping Thunder Client collection.

## Performance review and decisions

I seed 500 goals, 1,500 notes, 2,000 dated planner sessions and 50 focus intervals. I run PostgreSQL `ANALYZE` on the seeded tables, then execute the repositories' real bound SQL with `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)`. Only SELECT statements are explained. The JSON report contains execution plans, buffers, index names, query counts and pool reuse; it contains synthetic fixture IDs/dates in plan predicates, never development data or credentials, and does not dump SQL parameter tuples. [PostgreSQL explains why plans vary with data and statistics](https://www.postgresql.org/docs/current/using-explain.html).

| Topic | What I checked / chose |
| --- | --- |
| Indexes and composite indexes | Actual migrated indexes support owner + active position, owner + planner date, goal linkage and owner + focus start. The observed plans use those indexes. No redundant indexes/migrations were added. |
| N+1 queries | Goal pages of 1 and 20 both issue exactly two SQL statements, including serialization. Focus pages also issue two, with course labels joined in SQL. |
| Goal aggregates | Linked/completed session counts use indexed correlated scalar subqueries inside the SELECT. This avoids application N+1 round trips, but PostgreSQL still evaluates subplans per goal; I monitor this for larger pages. |
| Eager loading | Current responses use flat ORM entities, scalar aggregates and explicit joins, not traversed lazy relationships. Adding joinedload/selectinload without a relationship to load would not improve these paths. |
| Required data | Counts/summary calculations run in SQL; focus labels are projected in the same query. Resource pages fetch the fields required by their response schemas. Notes list responses still include content because that is the current frontend contract. |
| Pagination | Default 10, maximum 100 and offset maximum 10,000 are validated server-side. Unsupported sort fields are rejected. Full data export is an explicit streamed operation, not an unbounded normal list. |
| Contains search | Escaped parameterized ILIKE treats `%` literally. A leading-wildcard search is not accelerated by an ordinary title B-tree; my broad matching fixture may use the position index to stop at LIMIT. Selective/no-match searches at larger scale still need measurement before considering pg_trgm. |
| Connection pools | Async SQLAlchemy pooling has bounded size/overflow/timeout, recycle and pre-ping. Tests use size 3, overflow 0 and verify sequential backend connection reuse and return to baseline. Application defaults remain size 5 + overflow 5 per process; total DB demand also depends on worker count. |
| Async execution | Repositories await asyncpg/SQLAlchemy operations. Argon2 runs in a worker thread, logging queues without blocking on a full queue, and export file IO uses thread offloading. Async helps concurrent waiting, not CPU-bound work; I do not share an AsyncSession across concurrent requests. |
| Caching / Redis | Caching reuses a previously computed result. I retain request-local preference reuse only. Redis could later share short-lived dashboard/settings caches across workers, but would require TTLs, owner-scoped keys, invalidation and outage policy. No Redis service or dependency was added; timer/auth/ownership checks must remain authoritative. |

Small local EXPLAIN times demonstrate the query shape on this fixture; they are not latency SLOs. Warm buffers, one seeded owner, small datasets and no concurrent traffic limit the conclusions. I do not force PostgreSQL to choose an index or make flaky wall-clock assertions.

## Recorded verification

On 13 November 2026, I ran the complete suite on Windows with Python 3.14.2, pytest 9.1.1 and a fresh disposable PostgreSQL 18 cluster: **71 passed in 198.07 seconds**, with no skipped tests or failures. The cluster was stopped and removed after the run; my development database was not used. Fresh migrations and `alembic check` passed, as did `ruff check app tests`.

There was one non-failing upstream Starlette deprecation warning: the synchronous TestClient adapter currently prefers `httpx2` over its legacy HTTPX adapter. I keep this visible rather than suppress it. The main asynchronous integration suite uses HTTPX directly; I should review TestClient transport compatibility when updating those dependencies.

The following SELECT plan sample was captured during the earlier performance run on the same date; these are database execution times, separate from total suite runtime:

| Query | PostgreSQL execution time | Observed indexes |
| --- | --- | --- |
| goals | 0.355 ms | `ix_goal_owner_active_position`, `ix_study_session_owner_goal_active` |
| focus | 0.091 ms | `ix_focus_session_owner_started`, `pk_course` |
| notes | 0.042 ms | `ix_note_owner_active_position` |
| notes_contains_search | 0.056 ms | `ix_note_owner_active_position` |
| planner_date | 0.100 ms | `ix_study_session_owner_date_active` |

Goal and focus page SQL counts were both **2 for 1 item and 2 for 20 items**. Connection reuse/return checks passed. Full reproducible plan details are written to the ignored `backend/.test-artifacts/performance.json` when requested; the table above records this run rather than promising a fixed timing.

I validated the Postman collection JSON, but have not executed it in the Postman desktop application. I use Swagger steps as a manual guide; I have not automated those browser interactions. Browser UI automation, production concurrency/load tests, vulnerability scanning, CI and deployment checks remain separate work. This suite does not claim to prove every frontend interaction or production readiness.

## GitHub publication checks

For the 13 November 2026 repository review, I also passed frontend ESLint, strict TypeScript checks and an optimized Next.js build. Backend Ruff checks passed across application code, migrations and tests. The npm production-dependency advisory check reported zero known vulnerabilities at that time; this is not an audit of Python dependencies or a guarantee against unknown vulnerabilities.

I reviewed prospective commit contents through a temporary Git index, without staging or publishing my working project. Private environment files, dependencies, caches, build output and local reports were excluded; sanitized examples, npm's lockfile, migrations, tests and documentation were included. Secret-pattern checks found no matching private keys/provider tokens in the prospective source files. Pattern matching is not an exhaustive secret or history audit. I check `git diff --cached` myself immediately before my actual commit.

The README and architecture documents describe the current implementation in my developer voice. The browser checklist above remains a manual acceptance checklist, not a claim that every UI interaction was rerun during this review. I publish from the `studyflow` directory, not its parent containing unrelated projects.
