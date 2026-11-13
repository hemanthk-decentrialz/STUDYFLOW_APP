import { StudyFlowSettings } from "@/types/settings";

export function formatDate(date = new Date(), timeZone = "UTC"): string {
  return date.toLocaleDateString("en-US", { timeZone, weekday: "long", day: "numeric", month: "long", year: "numeric" });
}

export function calendarDate(date = new Date(), timeZone = "UTC"): string {
  const parts = new Intl.DateTimeFormat("en", { timeZone, year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(date);
  const part = (type: string) => parts.find((value) => value.type === type)!.value;
  return `${part("year")}-${part("month")}-${part("day")}`;
}

export function formatDateTime(value: string, settings: StudyFlowSettings): string {
  return new Intl.DateTimeFormat(undefined, { timeZone: settings.timeZone, dateStyle: "medium", timeStyle: "short", hour12: settings.timeFormat === "12h" }).format(new Date(value));
}

export function formatClock(value: string, timeFormat: StudyFlowSettings["timeFormat"]): string {
  const [hours, minutes] = value.split(":").map(Number);
  if (timeFormat === "24h") return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}`;
  return `${hours % 12 || 12}:${String(minutes).padStart(2, "0")} ${hours >= 12 ? "PM" : "AM"}`;
}
