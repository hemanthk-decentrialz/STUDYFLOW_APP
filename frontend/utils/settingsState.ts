import { StudyFlowSettings } from "@/types/settings";

export const DEFAULT_SETTINGS: StudyFlowSettings = {
  theme: "light", focusMinutes: 25, shortBreakMinutes: 5, longBreakMinutes: 15,
  completionSound: true, weekStartsOn: "monday", timeZone: "UTC", timeFormat: "24h",
  sessionReminders: false, deadlineReminders: false, reminderLeadMinutes: 15,
};
