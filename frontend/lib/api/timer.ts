import { ResourcePage } from "./resources";
import { apiRequest } from "@/lib/api/client";
import { FocusSession, FocusSummary, TimerState } from "@/types/timer";

export function getTimer() {
  return apiRequest<TimerState>("/api/v1/timers/current");
}

export type TimerPatch = Omit<TimerState, "endAt" | "lastCompletedAt" | "lastCompletedMode"> & {
  endAt?: number | null; lastCompletedAt?: number | null; lastCompletedMode?: TimerState["lastCompletedMode"] | null;
};
export function saveTimer(snapshot: TimerPatch) {
  return apiRequest<TimerState>("/api/v1/timers/current", {
    method: "PATCH",
    body: { expectedRevision: snapshot.revision, timer: { mode: snapshot.mode, timeLeft: snapshot.timeLeft, isRunning: snapshot.isRunning, courseId: snapshot.courseId } },
  });
}
export function getFocusSummary(zone: string, signal?: AbortSignal) {
  return apiRequest<FocusSummary>(`/api/v1/focus-sessions/summary?time_zone=${encodeURIComponent(zone)}`, { signal });
}
export function getFocusHistory(page = 1, courseId?: number, signal?: AbortSignal) {
  return apiRequest<ResourcePage<FocusSession>>(`/api/v1/focus-sessions?page=${page}&limit=10${courseId ? `&course_id=${courseId}` : ""}`, { signal });
}
