export type Priority = "High" | "Medium" | "Low";

export interface StudySession {
  courseId: number;
  goalId: number | null;
  id: number;
  subject: string;
  time: string;
  scheduledDate: string | null;
  durationMinutes: number;
  priority: Priority;
  completed: boolean;
}
