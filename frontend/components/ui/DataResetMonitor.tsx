"use client";

import { useEffect, useState } from "react";
import { currentReset, waitForReset } from "@/lib/api/resets";
import { resetWorkspace } from "@/lib/api/state";

export default function DataResetMonitor() {
  const [pending, setPending] = useState(false);
  useEffect(() => {
    let active = true;
    const changed = (event: Event) => setPending((event as CustomEvent<boolean>).detail);
    window.addEventListener("studyflow-reset-state", changed);
    void currentReset().then(async (job) => {
      if (!active || !job || !["queued", "running"].includes(job.status)) return;
      await resetWorkspace(() => waitForReset(job.id));
      if (active) location.reload();
    }).catch((error: unknown) => {
      if (active) window.dispatchEvent(new CustomEvent("studyflow-sync-error", {
        detail: error instanceof Error ? error.message : "Unable to restore reset status.",
      }));
    });
    return () => { active = false; window.removeEventListener("studyflow-reset-state", changed); };
  }, []);
  if (!pending) return null;
  return <div role="status" aria-live="polite" className="reset-overlay fixed inset-0 z-50 grid place-items-center p-6">
    <div className="reset-panel"><span className="hardware-badge hardware-warning"><span className="hardware-led" aria-hidden="true" />RESET IN PROGRESS</span><p>Resetting your study data. Please wait...</p></div>
  </div>;
}
