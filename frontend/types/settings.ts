export type ThemeMode = "light" | "dark";

export interface StudyFlowSettings {
  theme: ThemeMode;
  focusMinutes: number;
  shortBreakMinutes: number;
  longBreakMinutes: number;
  completionSound: boolean;
  weekStartsOn: "monday" | "sunday";
  timeZone: string;
  timeFormat: "12h" | "24h";
  sessionReminders: boolean;
  deadlineReminders: boolean;
  reminderLeadMinutes: number;
}

export interface DeletedResource {
  id: number;
  kind: "courses" | "notes" | "goals" | "study-sessions";
  title: string;
  deletedAt: string;
  courseId: number | null;
}

export interface StudyReminder {
  id: string;
  kind: "study-sessions" | "goals";
  title: string;
  dueAt: string;
}
