"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import useTimer from "@/hooks/useTimer";
import usePreferences from "@/hooks/usePreferences";
import { useAuth } from "@/context/AuthContext";
import { getDueReminders } from "@/lib/api/settings";
import { notify } from "@/components/ui/DataSyncStatus";
import { formatDateTime } from "@/utils/formatDate";

export default function StudyNotifications() {
  const router = useRouter();
  const { timer } = useTimer();
  const { user } = useAuth();
  const { settings, ready } = usePreferences();
  const [mounted] = useState(() => Date.now());
  const notified = useRef<number | undefined>(undefined);
  const audio = useRef<AudioContext | null>(null);
  const delivered = useRef(new Set<string>());
  useEffect(() => {
    const unlock = () => {
      try {
        if (!audio.current && "AudioContext" in window) audio.current = new AudioContext();
        if (audio.current?.state === "suspended") void audio.current.resume().catch(() => {});
      } catch { /* In-app feedback still works when audio is unavailable. */ }
    };
    window.addEventListener("pointerdown", unlock);
    window.addEventListener("keydown", unlock);
    return () => { window.removeEventListener("pointerdown", unlock); window.removeEventListener("keydown", unlock); void audio.current?.close().catch(() => {}); audio.current = null; };
  }, []);
  useEffect(() => {
    if (!ready || !timer.lastCompletedAt || timer.lastCompletedAt === notified.current) return;
    notified.current = timer.lastCompletedAt;
    if (timer.lastCompletedAt < mounted - 5000) return;
    notify(`${timer.lastCompletedMode ?? timer.mode} completed.`);
    if (settings.completionSound && audio.current?.state === "running") {
      const context = audio.current;
      const oscillator = context.createOscillator(), gain = context.createGain();
      oscillator.connect(gain); gain.connect(context.destination); oscillator.frequency.value = 660;
      gain.gain.setValueAtTime(.05, context.currentTime); gain.gain.exponentialRampToValueAtTime(.001, context.currentTime + .4);
      oscillator.start(); oscillator.stop(context.currentTime + .4);
      oscillator.onended = () => { oscillator.disconnect(); gain.disconnect(); };
    }
  }, [timer.lastCompletedAt, timer.lastCompletedMode, timer.mode, mounted, ready, settings.completionSound]);
  useEffect(() => {
    if (!ready || !user || (!settings.sessionReminders && !settings.deadlineReminders)) return;
    const owner = user.id;
    const controller = new AbortController();
    let inFlight = false;
    async function poll() {
      if (inFlight || controller.signal.aborted) return;
      inFlight = true;
      try {
        const reminders = await getDueReminders(controller.signal);
        for (const reminder of reminders) {
          if (controller.signal.aborted) break;
          const key = `user:${owner}:reminder:${reminder.kind}:${reminder.id}:${reminder.dueAt}`;
          const deliver = async () => {
            if (controller.signal.aborted || delivered.current.has(key)) return;
            try { if (localStorage.getItem(key)) return; localStorage.setItem(key, String(Date.now())); } catch { /* Fall back to document-scoped deduplication. */ }
            delivered.current.add(key);
            const message = `${reminder.kind === "goals" ? "Goal due" : "Study session"}: ${reminder.title} · ${formatDateTime(reminder.dueAt, settings)}`;
            notify(message, { action: { label: "Open", run: async () => { router.push(reminder.kind === "goals" ? "/goals" : "/planner"); } } });
            if (document.visibilityState === "hidden" && "Notification" in window && Notification.permission === "granted") {
              try { const notification = new Notification("Studyflow reminder", { body: message, tag: key }); notification.onclick = () => { window.focus(); notification.close(); }; } catch { /* Some mobile browsers allow notifications only through push/service workers. */ }
            }
          };
          if ("locks" in navigator) await navigator.locks.request(key, deliver); else await deliver();
        }
        try { Object.keys(localStorage).filter((key) => key.startsWith(`user:${owner}:reminder:`) && Number(localStorage.getItem(key)) < Date.now() - 172800000).forEach((key) => localStorage.removeItem(key)); } catch { /* Cleanup is optional when device storage is unavailable. */ }
      } catch { /* Poll again later; a transient failure must not interrupt studying. */ }
      finally { inFlight = false; }
    }
    void poll();
    const interval = setInterval(() => { void poll(); }, 30000);
    const refresh = () => { void poll(); };
    window.addEventListener("focus", refresh); window.addEventListener("studyflow-data-saved", refresh);
    return () => { controller.abort(); clearInterval(interval); window.removeEventListener("focus", refresh); window.removeEventListener("studyflow-data-saved", refresh); };
  }, [ready, user, settings, router]);
  return null;
}
