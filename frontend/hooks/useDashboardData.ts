"use client";

import usePreferences from "./usePreferences";
import { useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { getDashboardSummary } from "@/lib/api/dashboard";
import { DashboardSummary } from "@/types/api";

export default function useDashboardData() {
  const { settings } = usePreferences();
  const { user, isLoading: isAuthLoading } = useAuth();
  const [revision, setRevision] = useState(0);
  const [data, setData] = useState<{
    userId: string | null; summary: DashboardSummary | null; error: string | null;
  }>({ userId: null, summary: null, error: null });

  useEffect(() => {
    if (isAuthLoading || !user) return;
    const userId = user.id;
    let active = true;
    let requestVersion = 0;
    let inFlight = false;
    let refreshPending = false;
    let timeout: ReturnType<typeof setTimeout> | undefined;
    const load = async () => {
      if (inFlight) { refreshPending = true; return; }
      inFlight = true;
      const version = ++requestVersion;
      try {
        const summary = await getDashboardSummary(settings.timeZone);
        if (active && version === requestVersion) setData({ userId, summary, error: null });
      } catch (error) {
        if (active && version === requestVersion) setData((previous) => ({
          userId, summary: previous.userId === userId ? previous.summary : null,
          error: error instanceof Error ? error.message : "Unable to load dashboard.",
        }));
      } finally {
        inFlight = false;
        if (active && refreshPending) { refreshPending = false; void load(); }
      }
    };
    const refresh = () => { clearTimeout(timeout); timeout = setTimeout(() => { void load(); }, 100); };
    void load();
    const interval = setInterval(() => { if (document.visibilityState === "visible") refresh(); }, 60_000);
    window.addEventListener("studyflow-data-saved", refresh);
    window.addEventListener("focus", refresh);
    return () => {
      active = false; clearTimeout(timeout); clearInterval(interval);
      window.removeEventListener("studyflow-data-saved", refresh);
      window.removeEventListener("focus", refresh);
    };
  }, [isAuthLoading, user, revision, settings.timeZone]);

  return {
    summary: data.userId === user?.id ? data.summary : null,
    error: data.userId === user?.id ? data.error : null,
    isLoading: isAuthLoading || (!!user && data.userId !== user.id),
    retry: () => setRevision((previous) => previous + 1),
  };
}
