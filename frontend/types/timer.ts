export type TimerMode =
  | "Pomodoro"
  | "Short Break"
  | "Long Break";

export interface TimerState {
  revision: number;
  blockDuration: number;
  courseId: number | null;
  activeFocusId: string | null;
  mode: TimerMode;
  timeLeft: number;
  isRunning: boolean;
  completedSessions: number;
  endAt?: number;
  lastCompletedAt?: number;
  lastCompletedMode?: TimerMode;
}

export interface FocusSession {
  id: string; courseId: number | null; courseTitle: string;
  startedAt: string; endedAt: string | null; seconds: number;
  outcome: "running" | "paused" | "completed" | "cancelled";
}
export interface FocusSummary {
  weekStart: string; timeZone: string; seconds: number; completedPomodoros: number;
  days: { date: string; seconds: number }[];
  courses: { courseId: number | null; title: string; seconds: number }[];
}
