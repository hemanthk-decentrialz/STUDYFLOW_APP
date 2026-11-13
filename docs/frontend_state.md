# Frontend structure and integration

Studyflow uses Next.js App Router, React, TypeScript and Tailwind CSS. I keep business data in FastAPI/PostgreSQL; browser storage is limited to display/theme caches, tab markers and recoverable drafts.

[README](../README.md#local-setup) covers execution. [Backend architecture](backend_architecture.md) contains the API catalog and data invariants.

## Routes

| Route | Purpose | Main source |
| --- | --- | --- |
| /login, /signup | Account access | components/auth/{AuthLayout,LoginForm,SignupForm}.tsx |
| / | Today workspace | components/dashboard/Dashboard.tsx |
| /courses | Course management | app/(dashboard)/courses/page.tsx |
| /planner | Scheduling, completion and goal links | components/planner/{PlannerForm,PlannerCard}.tsx |
| /notes | Reading, editing and recovery | components/notes/{NoteCard,NoteEditor}.tsx |
| /goals | Deadlines, progress and session contributions | components/goals/{GoalCard,ProgressBar}.tsx |
| /timer | Focus/break timer and history | components/timer/{StudyTimer,FocusHistory}.tsx |
| /settings | Preferences and data controls | components/settings/Settings.tsx |
| /profile | Account information and display name | app/(dashboard)/profile/page.tsx |

Source paths are relative to frontend/. Protected pages share app/(dashboard)/layout.tsx and components/layout/DashboardLayout.tsx.

The normal journey is signup -> login -> create a course -> plan sessions, write notes or set goals -> focus -> review progress. Settings owns account-wide preferences; current-task controls stay on feature pages.

## Responsibilities

| Module | Purpose |
| --- | --- |
| app/layout.tsx, globals.css | Providers, metadata, first-paint theme and shared visual system |
| app/api/v1/[...path]/route.ts | Same-origin forwarding proxy; no feature persistence |
| context/AuthContext.tsx | Cookie-confirmed auth state and profile updates |
| lib/auth.ts | Tab/reload markers and auth-change signals |
| lib/api/client.ts | Fetch, credentials, error envelope, 204 and blob handling |
| lib/api/resources.ts | Resource paths, typed queries/mutations and restore |
| lib/api/{auth,timer,settings,dashboard,resets}.ts | Feature-specific contracts |
| lib/api/state.ts | Shared timer/preferences entries, ordered saves and reset coordination |
| hooks/useResourceList.ts | List state, pending mutations, refresh and Undo |
| hooks/usePreferences.ts | Shared settings and configured durations |
| hooks/useTimer.ts, utils/timerState.ts | Timer intent and local countdown calculation |
| components/ui/ResourceControls.tsx | Filter disclosure and useful pagination |
| components/ui/StudyLinks.tsx | Course/goal searchable comboboxes |
| components/ui/DataSyncStatus.tsx | Feedback, retry, Undo and confirmation dialog |
| components/ui/DataResetMonitor.tsx | Reset progress/recovery |
| components/settings/ThemeInitializer.tsx | Apply shared theme and maintain cache |
| components/timer/{TimerTicker,StudyNotifications}.tsx | Countdown, completion and reminder effects |
| types/, utils/ | API DTOs, formatting and default state |

I reuse these modules rather than creating duplicate API wrappers or state stores. I keep spacing and indentation consistent, trim redundant blank lines and reserve comments for behavior that is not obvious from the code. Formatting changes must preserve JSX text, string literals and framework directives.

## API integration

```text
Component/hook -> typed Fetch -> Next.js /api/v1 proxy -> FastAPI -> PostgreSQL
```

The proxy forwards allowed resource paths, cookies, origins, query parameters and selected response headers. BACKEND_URL is server-only; the proxy adds /api/v1, bounds request bodies and uses a 30-second upstream timeout.

Normal responses use { ok: true, data }; failures use { ok: false, error, details? }. The client handles empty 204 responses and explicit blob downloads.

DTO aliases include courseId, scheduledDate, expectedVersion and expectedRevision. Query names remain snake_case, including course_id, goal_id, sort_by and time_zone. The frontend planner module maps to the study-sessions API. Existing resource IDs are JavaScript-safe numbers; account/focus IDs are UUID strings.

Backend schemas are authoritative. I update DTOs, clients, hooks and UI together when contracts change. Generated TypeScript types have not been added.

## State and persistence

### Authentication

AuthContext verifies identity with users/me; local markers are not credentials. Login creates an HTTPOnly cookie, and logout revokes it.

I resume a tab using its sessionStorage marker and verify its cookie with users/me, without depending on PerformanceNavigationTiming. Refresh keeps the current route. A new tab without a marker asks for login; cross-tab account changes invalidate stale state. A restored page rechecks the session. Temporary network/server failures show a retry state on the same page instead of clearing a valid marker; 401 clears it. Closing a tab does not itself revoke the backend session.

### Lists and relationship pickers

Filtering, search, sorting and pagination execute on the backend. Normal lists default to 10 items, allow up to 100 and respect the offset bound. Previous/Next and page counters appear only when multiple pages exist.

A course/goal choice is one searchable combobox. Scrolling requests bounded 100-item batches; typing searches the full owned collection. Arrow keys, Enter and Escape work, selected labels resolve outside the loaded batch, and arbitrary typed text cannot become a relationship. Picker batching is independent of normal page size.

Mutations expose pending/errors and refresh affected views. Delete offers real Undo; Recently deleted provides later recovery. Parent-course and duplicate conflicts remain backend-enforced.

### Notes

New notes remain device drafts until Create. Existing notes autosave valid changes after 900 ms idle. Drafts are account/note/context scoped and flushed on page hide/unmount where storage is available.

PATCH includes expectedVersion. Conflicts preserve local text and require an explicit server/local choice. Recovered drafts require review before autosave resumes. Failed/in-flight saves do not silently discard new typing. Device storage assists recovery; it is not the notes database.

### Timer and preferences

Shared entries serialize saves and reconcile authoritative responses. Countdown ticks update the UI without a request or storage write every second. The server owns deadlines, revisions and completion counts; stale revisions reload current state.

Settings contains durations, sound, calendar and reminders. The shared workspace header has an accessible retro light/dark switch that applies and persists immediately. Theme changes preserve unsaved Settings drafts; Save preferences preserves the current theme. Saving preferences refreshes timer revision/state: fresh idle blocks adopt new values, while running/paused blocks retain their duration/remainder. Completion remains at 00:00; Start/Reset and mode selection are explicit.

History uses recorded intervals and timezone-aware weekly totals. Manual goal progress and linked-session counts remain separate values.

### Notifications and data controls

StudyNotifications polls enabled reminders every 30 seconds, handles timer feedback/sound and deduplicates delivery by account/resource/due time using storage/locks when available. Sound needs a user gesture. Old delivery markers are pruned.

Reminders require an open application. Allow browser notifications requests permission on the current device; it does not enable reminder preferences or closed-site delivery. I enable session/deadline reminders separately and save preferences. Foreground delivery uses in-app feedback; a supported, permitted background tab can show a system notification. Goal deadlines use 09:00 in the chosen zone, with lead time applied before it.

Export uses authenticated blob transport and an icon-only download button with an accessible label and tooltip. The backend produces indented UTF-8 JSON, which is plain text readable in an editor; I keep the .json extension to identify its structured format. Recently deleted reuses restore endpoints. Reset confirms permanent deletion, follows the persisted job, clears relevant device state and reloads while retaining account/preferences. Backup import and closed-site delivery are not implemented.

## Visual system and navigation

I use the Outrun Studio theme: sunwashed peach canvas (#F5E2DC), seashell cards (#FCF3F0), charcoal text (#1E242B), teal actions (#0F766E) and terracotta borders (#DFC1B8) in light mode; green-black canvas (#0C1713), emerald cards (#13241E), mint text (#D1FAE5), phosphor-green actions (#34D399) and matrix borders (#223F35) in dark mode. globals.css owns shared tokens, hover states and status roles. I use a local JetBrains Mono / Space Mono / system monospace stack for headings and hardware-style feedback, with system UI text for reading. No font download is required; a named font appears only when installed.

- Desktop navigation collapses; mobile has shortcuts and a drawer with Escape, focus handling and an inert background.
- Filters are a labelled disclosure beside the title.
- Hover states use shared teal/phosphor-green accent tokens in both themes, with red feedback for destructive actions and visible keyboard focus. Disabled controls do not use active hover states.
- Related-resource links are compact labeled controls without diagonal arrows; the header profile link has a button border and hover state. Today has no extra Plan a session action beside its heading.
- Resource forms share a form/content grid that stacks on narrow screens.
- Notes use a reading layout; the timer has one dominant clock.
- Goal progress retains its thresholds: red below 40%, amber from 40%, the primary teal/phosphor-green from 70%, a separate completion green at 100%; zero is empty.
- Sync success uses dedicated electric-cyan tokens (#0284C7 / #38BDF8), reset progress uses amber (#D97706 / #FBBF24), and destructive feedback uses rose (#E11D48 / #FB7185). I keep completion green separate from sync blue so a palette change does not blur those roles. Darker light-mode status text keeps small labels readable while preserving those accent colours.
- Primary text, muted text, primary-button labels and status-text/card pairs were checked at 4.5:1 or better in both themes. This is a targeted contrast check, not complete accessibility certification.
- The initial auth guard uses Loading Studyflow, not dashboard-specific copy. I defer only its visible spinner/text by 200 ms to avoid flashes on fast login redirects; I do not add a minimum wait or render protected content before verification. After authentication, each page keeps its own data-loading message.
- Cards and primary buttons use crisp 1.5px borders and 2px hard offset shadows instead of blurry elevation.
- Sync/error notices use an 8px LED dot and monospace bordered badge. Reset progress uses an amber LED; destructive actions use rose.
- The full-page loader uses animated accent-coloured segments on the canvas background. It is indeterminate and has no fabricated percentage; its progressbar label and status text remain accessible and reduced-motion preferences are respected.
- Pickers, feedback notices and reset overlays share the same palette rather than hardcoded blue or white surfaces.

I keep one same-purpose destination per card/state. Today's empty plan has Add a session, without an extra Open planner footer. View all sessions appears only for a shortened summary. The deadlines card has one goals link. The sidebar account footer is informational, and Profile no longer repeats the email inside Account details.

Global navigation and links to different filtered contexts remain intentional. Controls with different outcomes, such as saving a note versus keeping its unsaved device draft, are not duplicates.

## Verification and maintenance

Use the [README checks](../README.md#development-checks). Review empty/populated, loading/error, overflow and narrow-screen states after changes. Check conditional navigation and both one-page/multiple-page lists.

Development verification has covered desktop/mobile layouts, dark mode, course selection, filters, timer controls, note conflicts, exports and restore. Frontend browser checks remain manual. Backend pytest coverage now checks the API contracts, cookie sessions and persistence behind these screens; the [testing guide](testing-guide.md) explains coverage and reproduction. This is not proof of deployment readiness, and deployment scaffolding has not been added.
