export interface Note {
  version: number;
  updatedAt: string;
  courseId: number;
  id: number;
  title: string;
  subject: string;
  content: string;
}
export interface NotePatch {
  expectedVersion: number;
  title?: string;
  content?: string;
  courseId?: number;
}
export type NoteInput = Omit<Note, "version" | "updatedAt">;
