export interface Goal {
  courseId: number;
  linkedSessionCount?: number;
  completedSessionCount?: number;
  id: number;
  title: string;
  subject: string;
  deadline: string;
  progress: number;
}
