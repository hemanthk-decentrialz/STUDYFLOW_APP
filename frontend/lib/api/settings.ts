import { apiRequest } from "@/lib/api/client";
import { DeletedResource, StudyFlowSettings, StudyReminder } from "@/types/settings";

export function getSettings() {
  return apiRequest<StudyFlowSettings>("/api/v1/preferences");
}

export function saveSettings(settings: Partial<StudyFlowSettings>) {
  return apiRequest<StudyFlowSettings>("/api/v1/preferences", {
    method: "PATCH",
    body: { settings },
  });
}

export { requestReset as resetStudyData } from "./resets";


export function getDeletedResources(page = 1, kind = "", signal?: AbortSignal) {
  return apiRequest<import("./resources").ResourcePage<DeletedResource>>(`/api/v1/deleted-resources?page=${page}&limit=10${kind ? `&kind=${encodeURIComponent(kind)}` : ""}`, { signal });
}

export function getDueReminders(signal?: AbortSignal) {
  return apiRequest<StudyReminder[]>("/api/v1/reminders", { signal });
}

export function exportStudyData() {
  return apiRequest<Blob>("/api/v1/data-exports", { responseType: "blob" });
}
