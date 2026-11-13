import { apiRequest } from "@/lib/api/client";
import { DashboardSummary } from "@/types/api";

export function getDashboardSummary(timeZone: string) {
  return apiRequest<DashboardSummary>(`/api/v1/dashboards/summary?time_zone=${encodeURIComponent(timeZone)}`);
}
