# Studyflow

A student productivity workspace for planning study sessions, keeping course notes, tracking goals and recording focused study time.

I built Studyflow with a Next.js frontend and an asynchronous FastAPI backend. PostgreSQL is the source of truth; browser requests use a same-origin API proxy and cookie sessions.

## Features

- **Today:** next study session, daily agenda, deadlines and weekly focus.
- **Courses and planner:** owned course relationships, dated sessions, priorities, completion and optional goal links.
- **Notes:** editing, explicit saving, device-draft recovery and version-conflict handling.
- **Goals:** deadlines, manual progress and linked-session counts.
- **Focus:** configurable study/break durations and server-timed history.
- **Settings:** calendar preferences, reminders, JSON export, Recently deleted and study-data reset.
- **Profile:** display-name editing, account details and sign-out.

The shared workspace header provides an immediate, automatically saved light/dark theme switch with a crisp circular reveal. Reduced-motion preferences and browsers without View Transitions receive immediate theme changes. The interface supports desktop/mobile layouts, collapsible navigation, searchable course selection and contextual filters. I use the Outrun Studio theme: sunwashed peach canvas (#F5E2DC), seashell cards (#FCF3F0) and teal controls (#0F766E) in light mode; green-black canvas (#0C1713), emerald cards (#13241E) and phosphor-green controls (#34D399) in dark mode. Crisp borders, offset shadows, existing monospace fonts and the segmented loader preserve the retro character. Sync feedback uses cyan, warnings/reset progress use amber, and destructive alerts use rose.

## Stack

| Area | Technology |
| --- | --- |
| Frontend | Next.js 16.4.6, React 19, TypeScript, Tailwind CSS 4, Font Awesome |
| Backend | FastAPI, Pydantic v2, pydantic-settings |
| Data | PostgreSQL, SQLAlchemy 2.0 async ORM, asyncpg, Alembic |
| Authentication | Argon2 password hashes and revocable HTTPOnly cookie sessions |
| Transport | Typed Fetch clients -> Next.js proxy -> FastAPI /api/v1 |

## Repository

```text
studyflow/
|-- frontend/              # Next.js application and same-origin API proxy
|-- backend/
|   |-- app/               # Controllers, services, repositories and data models
|   |-- alembic/           # Versioned PostgreSQL migrations
|   |-- tests/             # Unit, API integration and measured-query checks
|   |-- .env.example
|   `-- .env.test.example
|-- docs/
|   |-- backend_architecture.md
|   |-- frontend_state.md
|   |-- testing-guide.md
|   `-- postman/           # Collection and blank local environment template
|-- .gitattributes          # Shared source line-ending policy
|-- .gitignore
|-- AGENTS.md              # Repository engineering conventions
`-- README.md
```

## Local setup

### Prerequisites

- Python **3.12+**, as declared in the backend package.
- Node.js **20.9+**, required by the installed Next.js package, and npm.
- A running PostgreSQL server. Local database verification has used PostgreSQL 18.

Commands below use **PowerShell**, starting in the `studyflow` directory. Preserve existing environment files and database data.

### 1. Create the PostgreSQL role and database

Open PostgreSQL SQL Shell (`psql`) and connect as an administrator. Create one application role:

```sql
CREATE ROLE studyflow_app LOGIN;
```

In psql, set its password interactively:

```text
\password studyflow_app
```

Then create the database:

```sql
CREATE DATABASE studyflow OWNER studyflow_app;
```

Alternatively, in pgAdmin create a login role, set its password in Definition, then create the database with that role as owner. Use one approach.

Alembic creates all tables and indexes. Existing installations should use their existing role/database; do not recreate them or manually create module tables.

### 2. Configure the environment

Copy the examples only when the local files do not already exist:

```powershell
if (-not (Test-Path -LiteralPath backend/.env)) {
    Copy-Item backend/.env.example backend/.env
}
if (-not (Test-Path -LiteralPath frontend/.env.local)) {
    Copy-Item frontend/.env.example frontend/.env.local
}
```

Edit `backend/.env`. Replace the example database URL with your own credentials:

```dotenv
DATABASE_URL=postgresql+asyncpg://studyflow_app:REPLACE_WITH_URL_ENCODED_PASSWORD@localhost:5432/studyflow
APP_ENV=development
ALLOWED_ORIGINS=["http://localhost:3000","http://127.0.0.1:3000"]
API_ORIGIN=http://localhost:8000
TRUSTED_HOSTS=["localhost","127.0.0.1"]
COOKIE_SECURE=false
SESSION_COOKIE_NAME=studyflow_session
DOCS_ENABLED=true
LOG_LEVEL=INFO
```

URL-encode reserved characters in the password, for example `@` -> `%40` and `#` -> `%23`. Keep the other pool, rate-limit and body-size values from the example initially. Shell environment variables override the file.

Set `frontend/.env.local` to:

```dotenv
BACKEND_URL=http://127.0.0.1:8000
TRUST_PROXY_HEADERS=false
MAX_REQUEST_BYTES=524288
```

`BACKEND_URL` is a server-only origin, without `/api/v1`. The frontend needs no database credentials, JWT key or public backend URL. Real credentials belong only in ignored local environment files.

If ports change, update the backend target, API origin and allowed frontend origins accordingly. Restart the affected server after environment changes.

### 3. Start the backend

```powershell
Set-Location backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Using the environment's Python directly makes script activation optional. Current migration head: **0011**. Existing checkouts should apply forward migrations before running updated code.

### 4. Start the frontend

Open a second terminal in the project directory:

```powershell
Set-Location frontend
npm ci
npm run dev -- --port 3000
```

| Service | URL |
| --- | --- |
| Website | http://localhost:3000 |
| Swagger UI | http://localhost:8000/api/v1/docs |
| PostgreSQL readiness | http://localhost:8000/api/v1/health |

### 5. First use and Swagger

Create an account, sign in, add a course, then create sessions, notes and goals. Set your time zone and focus preferences in Settings; the default zone is UTC.

In Swagger, execute `POST /api/v1/sessions`, then `GET /api/v1/users/me`. The browser sends the cookie automatically. There is no JWT/Bearer token to paste into Authorize. Use consistent hostnames when sharing browser cookies.

Refreshing an authenticated tab verifies the cookie and keeps the current page. I use a tab-scoped marker rather than depending on browser navigation timing. A new tab without that marker asks for login; temporary verification failures offer retry on the current page. Closing a tab does not revoke the server session; logout explicitly revokes it.

## Development checks

From `frontend/`:

```powershell
npm run lint
npx tsc --noEmit --noUnusedLocals --noUnusedParameters
npm run build
```

From `backend/`:

```powershell
.\.venv\Scripts\python.exe -m ruff check app alembic tests
.\.venv\Scripts\python.exe -m compileall -q app alembic
.\.venv\Scripts\python.exe -m alembic current
.\.venv\Scripts\python.exe -m alembic check
```

The last two commands require the configured database. I maintain pytest unit, API/PostgreSQL integration and measured-query tests. See [the testing guide](docs/testing-guide.md) for the dedicated test database, commands, Swagger workflow and Postman collection. CI has not been added.

For manual browser, Swagger and Postman workflows, I use the [testing guide](docs/testing-guide.md#manual-website-acceptance-checklist). For automated tests, I create the separate test database described there, then run from `backend/`:

```powershell
.\.venv\Scripts\python.exe -m pytest tests --require-db -q
```

I never point test cleanup at my development database. Without a test database, I can run the isolated checks with `-m unit` instead of `--require-db`.

## Current boundaries

| Area | Implemented behavior |
| --- | --- |
| Timer completion | Stops at 00:00; does not automatically reset or start another mode. |
| Reminders | Open-app delivery only; browser notifications also need device permission/support. |
| Export | Pretty-printed JSON text download includes deleted study records; excludes credentials/auth sessions. Import is not implemented. |
| Deletion | Study resources are soft-deleted/restorable. Reset permanently removes study data/history while preserving the account/preferences. |
| Rate limits | Per-process memory, not shared across backend workers. |
| Background work | Native tasks with persisted reset jobs/recovery; no external worker queue. |
| Deployment | Configuration safeguards exist; deployment automation and final deployment validation remain separate work. |

## Troubleshooting

- **Virtual environment copy/activation errors:** close processes using the environment and check installed Python versions with `py --list`. Direct Python execution avoids activation-policy issues. For persistent OneDrive locks, use a non-synced environment directory and its Python executable.
- **npm EBUSY:** stop the project's development server and release editor/synchronization locks on node_modules before retrying.
- **Database connection errors:** check the service, port, role/database names and URL-encoded password.
- **Proxy 503:** confirm the backend is running and BACKEND_URL contains its origin.
- **Login/CORS issues:** keep browser hostnames consistent and verify explicit origins, proxy and cookie settings.

## Engineering documentation

- [Backend architecture and API catalog](docs/backend_architecture.md)
- [Frontend structure and integration](docs/frontend_state.md)
- [Testing, manual acceptance checks and measured performance](docs/testing-guide.md)
- [Postman collection](docs/postman/studyflow.collection.json) and [blank environment template](docs/postman/local.environment.json)

I keep these documents aligned with the current implementation, reuse existing responsibilities, preserve applied migrations and remove confirmed unused code without deleting framework-required callbacks.

## Publishing this repository

I publish the `studyflow` directory as the repository root so unrelated projects beside it are not included. I commit source, npm's lockfile, migrations, tests, documentation and sanitized environment examples. I keep local environment files, virtual environments, dependencies, build/cache output, logs, downloaded exports and test reports out of Git.

Before my first commit, I run the development checks and review the exact staged file list. From the `studyflow` directory, for a new repository only:

```powershell
git init -b main
git add .
git status --short
git diff --cached --stat
git diff --cached --check
# Each real environment file below must be reported as ignored:
git check-ignore backend/.env backend/.env.test frontend/.env.local
# No output is expected: these files must not be staged/tracked.
git ls-files -- backend/.env backend/.env.test frontend/.env.local
```

If this directory already has a repository, I skip `git init`. I inspect staged file contents locally before committing. `.gitignore` does not remove already tracked files; if one of my local environment files is tracked, I remove it from the index with `git rm --cached -- <path>` while keeping the local copy. If credentials were committed previously, removing the current file is insufficient: I rotate the exposed credentials before publishing.

After reviewing, I create an empty GitHub repository, then use its actual URL:

```powershell
git commit -m "Initial Studyflow application"
git remote add origin https://github.com/YOUR_USERNAME/studyflow.git
git push -u origin main
```

I do not create another README or `.gitignore` on GitHub when pushing this existing project. If an `origin` remote already exists, I inspect `git remote -v` rather than adding a duplicate. Repository visibility and a license are choices I make before sharing; a license has not been selected in this project. Passing local checks establishes a verified development baseline, not a completed deployment or security audit.
