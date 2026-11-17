import { Course } from "@/types/course";
import { Goal } from "@/types/goal";
import { Note, NotePatch } from "@/types/note";
import { StudySession } from "@/types/planner";
import { apiRequest } from "./client";

export type ResourceModule = "notes" | "goals" | "planner" | "courses";
export interface ResourceQuery {
  course_id?: number; goal_id?: number; has_completed_focus?: boolean;
  date_from?: string; date_to?: string;
  page?: number; limit?: number; search?: string; subject?: string; title?: string;
  sort_by?: string; order?: "asc" | "desc"; completed?: boolean; priority?: string;
  progress_min?: number; progress_max?: number; deadline_from?: string; deadline_to?: string;
}
export interface ResourcePage<T> {
  items: T[]; page: number; limit: number; total: number; total_pages: number;
}
export type ResourceInput<T> = Omit<T, "version" | "updatedAt" | "linkedSessionCount" | "completedSessionCount">;
export interface ResourceApi<T extends { id: number }> {
  module: ResourceModule;
  list: (query?: ResourceQuery, signal?: AbortSignal) => Promise<ResourcePage<T>>;
  create: (payload: ResourceInput<T>) => Promise<T>;
  remove: (id: number) => Promise<void>;
}

export interface MutableResourceApi<T extends { id: number }> extends ResourceApi<T> {
  patch: (id: number, payload: Partial<Omit<T, "id">>) => Promise<T>;
}

function resourcePath(module: ResourceModule): string {
  return `/api/v1/${module === "planner" ? "study-sessions" : module}`;
}

export function resourceApi<T extends { id: number }>(module: ResourceModule): ResourceApi<T> {
  const path = resourcePath(module);
  return {
    module,
    list(query = {}, signal) {
      const params = new URLSearchParams();
      Object.entries(query).forEach(([key, value]) => {
        if (value !== undefined && value !== "") params.set(key, String(value));
      });
      return apiRequest<ResourcePage<T>>(`${path}?${params}`, { signal });
    },
    create: (body) => apiRequest<T>(path, { method: "POST", body: "courseId" in body ? Object.fromEntries(Object.entries(body).filter(([key]) => key !== "subject")) : body }),
    remove: (id) => apiRequest<void>(`${path}/${id}`, { method: "DELETE" }),
  };
}

function mutableResourceApi<T extends { id: number }>(
  module: Exclude<ResourceModule, "notes">
): MutableResourceApi<T> {
  return {
    ...resourceApi<T>(module),
    patch: (id, body) => apiRequest<T>(`${resourcePath(module)}/${id}`, { method: "PATCH", body }),
  };
}

export const noteApi = {
  ...resourceApi<Note>("notes"),
  get: (id: number) => apiRequest<Note>(`/api/v1/notes/${id}`),
  patch: (id: number, body: NotePatch) => apiRequest<Note>(`/api/v1/notes/${id}`, { method: "PATCH", body }),
};
export function restoreResource<T>(module: ResourceModule, id: number) {
  return apiRequest<T>(`${resourcePath(module)}/${id}/restore`, { method: "POST" });
}
export const goalApi = mutableResourceApi<Goal>("goals");
export const plannerApi = mutableResourceApi<StudySession>("planner");

export const courseApi = mutableResourceApi<Course>("courses");
