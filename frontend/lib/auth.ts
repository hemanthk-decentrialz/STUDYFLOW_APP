import { SessionUser } from "@/types/auth";

const SESSION_KEY = "studyflow-session";
export const AUTH_EVENT_KEY = "studyflow-auth-event";
let authenticatedInThisDocument = false;

// This tab-scoped record is a reload marker, never an authentication credential.
export function getSession(): SessionUser | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = sessionStorage.getItem(SESSION_KEY);
    if (!raw) return null;
    const user = JSON.parse(raw) as Partial<SessionUser>;
    return typeof user.id === "string" && typeof user.name === "string" &&
      typeof user.email === "string" && typeof user.createdAt === "string"
      ? user as SessionUser : null;
  } catch { return null; }
}

export function canResumeSession(): boolean {
  if (typeof window === "undefined") return false;
  // A verified tab marker survives refresh without depending on navigation timing support.
  return authenticatedInThisDocument || getSession() !== null;
}

export function saveSession(user: SessionUser): void {
  authenticatedInThisDocument = true;
  try { sessionStorage.setItem(SESSION_KEY, JSON.stringify(user)); }
  catch { /* The current document can still use its verified in-memory user. */ }
}

export function clearSession(): void {
  authenticatedInThisDocument = false;
  try { sessionStorage.removeItem(SESSION_KEY); } catch { /* Storage may be unavailable. */ }
  try { localStorage.removeItem(SESSION_KEY); } catch { /* Remove the former persistent cache. */ }
}

export function announceAuthChange(): void {
  try {
    // Cookies are shared across tabs: other open tabs must reauthenticate after a switch.
    localStorage.setItem(AUTH_EVENT_KEY, `${Date.now()}:${Math.random()}`);
  } catch { /* The backend still verifies every authenticated request. */ }
}
