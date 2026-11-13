export interface ApiSuccess<T> {
  ok: true;
  data: T;
  message?: string;
}

export interface ApiFailure {
  ok: false;
  error: string;
  details?: string[];
}

export type ApiResponse<T> =
  | ApiSuccess<T>
  | ApiFailure;

export interface DashboardSummary {
  date: string;
  timeZone: string;
  todaySessions: import("./planner").StudySession[];
  nextSession: import("./planner").StudySession | null;
  upcomingGoals: import("./goal").Goal[];
  todaySessionCount: number;
  todayCompletedCount: number;
  todayPlannedMinutes: number;
  undatedPlannerCount: number;
  overdueGoalCount: number;
  plannerCount: number;
  completedGoals: number;
  pendingGoals: number;
  totalGoals: number;
  completionRate: number;
  completedPlanner: number;
  pendingPlanner: number;
  plannerCompletionRate: number;
  totalNotes: number;
  totalSessions: number;
  activeGoalTitle: string;
}
