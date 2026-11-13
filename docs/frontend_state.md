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

Refresh can resume a verified tab. Fresh navigation asks for login again; cross-tab auth signals and restored-page handling invalidate stale client state. Closing a tab does not itself revoke the backend session.

### Lists and relationship pickers

Filtering, search, sorting and pagination execute on the backend. Normal lists default to 10 items, allow up to 100 and respect the offset bound. Previous/Next and page counters appear only when multiple pages exist.

A course/goal choice is one searchable combobox. Scrolling requests bounded 100-item batches; typing searches the full owned collection. Arrow keys, Enter and Escape work, selected labels resolve outside the loaded batch, and arbitrary typed text cannot become a relationship. Picker batching is independent of normal page size.

Mutations expose pending/errors and refresh affected views. Delete offers real Undo; Recently deleted provides later recovery. Parent-course and duplicate conflicts remain backend-enforced.

### Notes

New notes remain device drafts until Create. Existing notes autosave valid changes after 900 ms idle. Drafts are account/note/context scoped and flushed on page hide/unmount where storage is available.

PATCH includes expectedVersion. Conflicts preserve local text and require an explicit server/local choice. Recovered drafts require review before autosave resumes. Failed/in-flight saves do not silently discard new typing. Device storage assists recovery; it is not the notes database.

### Timer and preferences

Shared entries serialize saves and reconcile authoritative responses. Countdown ticks update the UI without a request or storage write every second. The server owns deadlines, revisions and completion counts; stale revisions reload current state.

Settings contains durations, sound, theme, calendar and reminders. Saving preferences refreshes timer revision/state: fresh idle blocks adopt new values, while running/paused blocks retain their duration/remainder. Completion remains at 00:00; Start/Reset and mode selection are explicit.

History uses recorded intervals and timezone-aware weekly totals. Manual goal progress and linked-session counts remain separate values.

### Notifications and data controls

StudyNotifications polls enabled reminders every 30 seconds, handles timer feedback/sound and deduplicates delivery by account/resource/due time using storage/locks when available. Sound needs a user gesture. Old delivery markers are pruned.

Reminders require an open application. Browser notifications additionally need explicit device permission/support. Goal deadlines use 09:00 in the chosen zone, with lead time applied before it.

Export uses authenticated blob transport. Recently deleted reuses restore endpoints. Reset confirms permanent deletion, follows the persisted job, clears relevant device state and reloads while retaining account/preferences. Backup import and closed-site delivery are not implemented.

## Visual system and navigation

I use paper-toned surfaces, ink-blue actions, editorial headings and system UI text. globals.css owns light/dark tokens and shared styling; the installed fonts/icons avoid external assets. References for the direction were [Sunsama](https://www.sunsama.com/), [Things](https://culturedcode.com/things/) and [Craft](https://www.craft.do/), without copying their assets.

- Desktop navigation collapses; mobile has shortcuts and a drawer with Escape, focus handling and an inert background.
- Filters are a labelled disclosure beside the title.
- Resource forms share a form/content grid that stacks on narrow screens.
- Notes use a reading layout; the timer has one dominant clock.
- Goal progress remains red below 40%, amber from 40%, blue from 70%, green at 100%; zero is empty.
- Primary/muted text and button contrast pairs were checked in both themes, without claiming complete accessibility certification.

I keep one same-purpose destination per card/state. Today's empty plan has Add a session, without an extra Open planner footer. View all sessions appears only for a shortened summary. The deadlines card has one goals link. The sidebar account footer is informational, and Profile no longer repeats the email inside Account details.

Global navigation and links to different filtered contexts remain intentional. Controls with different outcomes, such as saving a note versus keeping its unsaved device draft, are not duplicates.

## Verification and maintenance

Use the [README checks](../README.md#development-checks). Review empty/populated, loading/error, overflow and narrow-screen states after changes. Check conditional navigation and both one-page/multiple-page lists.

Development verification has covered desktop/mobile layouts, dark mode, course selection, filters, timer controls, note conflicts, exports and restore. Frontend browser checks remain manual. Backend pytest coverage now checks the API contracts, cookie sessions and persistence behind these screens; the [testing guide](testing-guide.md) explains coverage and reproduction. This is not proof of deployment readiness, and deployment scaffolding has not been added.
