import { SetStateAction } from "react";
import { ApiRequestError, invalidateApiRequests } from "./client";
import { getSettings, saveSettings } from "./settings";
import { getTimer, saveTimer } from "./timer";
import { StudyFlowSettings } from "@/types/settings";
import { TimerState } from "@/types/timer";
import { DEFAULT_TIMER_STATE } from "@/utils/timerState";

type Entry<T> = {
  key: string; cacheKey: string; value: T; loaded: boolean; active: boolean;
  listeners: Set<() => void>; pending: SetStateAction<T>[];
  version: number; savedVersion: number;
  loading?: Promise<void>; saving?: Promise<void>;
};

const entries = new Map<string, Entry<unknown>>();
let resetting = false;
let resetPromise: Promise<void> | null = null;

export function getEntry<T>(userId: string, key: string, initial: T): Entry<T> {
  const cacheKey = `user:${userId}:${key}`;
  let entry = entries.get(cacheKey) as Entry<T> | undefined;
  if (!entry) {
    // Use defaults until the authenticated GET resolves.
    entry = { key, cacheKey, value: initial, loaded: false, active: true,
      listeners: new Set(), pending: [], version: 0, savedVersion: 0 };
    entries.set(cacheKey, entry as Entry<unknown>);
  }
  return entry;
}

function notify<T>(entry: Entry<T>, cache = true): void {
  if (!entry.active) return;
  if (cache && typeof window !== "undefined") {
    try { localStorage.setItem(entry.cacheKey, JSON.stringify(entry.value)); }
    catch { /* A full browser cache does not prevent server persistence. */ }
  }
  entry.listeners.forEach((listener) => listener());
}

function report(error: unknown): void {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent("studyflow-sync-error", {
      detail: error instanceof Error ? error.message : "Unable to sync your changes.",
    }));
  }
}

async function read(key: string): Promise<unknown> {
  switch (key) {
    case "study-timer": return getTimer();
    case "settings": return getSettings();
    default: throw new Error(`Unsupported storage key: ${key}`);
  }
}

async function persist(key: string, value: unknown): Promise<unknown> {
  switch (key) {
    case "study-timer": {
      const timer = value as TimerState;
      return saveTimer({ ...timer, endAt: timer.endAt ?? null,
        lastCompletedAt: timer.lastCompletedAt ?? null,
        lastCompletedMode: timer.lastCompletedMode ?? null });
    }
    case "settings": return saveSettings(value as StudyFlowSettings);
    default: throw new Error(`Unsupported storage key: ${key}`);
  }
}

function apply<T>(value: T, action: SetStateAction<T>): T {
  return typeof action === "function" ? (action as (previous: T) => T)(value) : action;
}

export async function loadEntry<T>(entry: Entry<T>): Promise<void> {
  if (!entry.active || entry.loaded || resetting) return;
  if (entry.loading) return entry.loading;
  entry.loading = (async () => {
    const value = await read(entry.key) as T;
    if (!entry.active) return;
    entry.value = entry.pending.reduce(apply<T>, value);
    entry.loaded = true;
    if (entry.pending.length) entry.version++;
    entry.pending = [];
    notify(entry);
  })();
  try { await entry.loading; }
  finally { entry.loading = undefined; }
  if (entry.active && entry.version > entry.savedVersion) await saveEntry(entry);
}

async function saveEntry<T>(entry: Entry<T>): Promise<void> {
  if (!entry.active || !entry.loaded || resetting) return;
  if (entry.saving) return entry.saving;
  entry.saving = (async () => {
    while (entry.active && !resetting && entry.savedVersion < entry.version) {
      const version = entry.version;
      const desired = entry.value;
      let saved: T;
      try { saved = await persist(entry.key, desired) as T; }
      catch (failure) {
        if (entry.key !== "study-timer" || !(failure instanceof ApiRequestError) || failure.status !== 409) throw failure;
        const fresh = await read(entry.key) as TimerState;
        if (!entry.active) return;
        const wasCompletion = !(desired as TimerState).isRunning && (desired as TimerState).timeLeft === 0 && !fresh.isRunning && fresh.timeLeft === 0;
        entry.value = fresh as T;
        entry.savedVersion = entry.version;
        notify(entry);
        if (!wasCompletion) throw failure;
        saved = fresh as T;
      }
      if (!entry.active) return;
      entry.savedVersion = version;
      if (entry.key === "study-timer" && entry.version !== version) {
        entry.value = { ...entry.value, revision: (saved as TimerState).revision, activeFocusId: (saved as TimerState).activeFocusId };
      }
      if (entry.version === version) {
        entry.value = saved;
        notify(entry);
      }
      window.dispatchEvent(new Event("studyflow-data-saved"));
    }
  })();
  try { await entry.saving; }
  finally { entry.saving = undefined; }
}

export function updateEntry<T>(entry: Entry<T>, action: SetStateAction<T>): void {
  if (!entry.active || resetting) return;
  const next = apply(entry.value, action);
  if (JSON.stringify(next) === JSON.stringify(entry.value)) return;
  const oldTimer = entry.key === "study-timer" ? entry.value as TimerState : null;
  const newTimer = entry.key === "study-timer" ? next as TimerState : null;
  const localTickOnly = oldTimer?.isRunning && newTimer?.isRunning &&
    JSON.stringify({ ...oldTimer, timeLeft: 0 }) === JSON.stringify({ ...newTimer, timeLeft: 0 });
  entry.value = next;
  if (localTickOnly) { notify(entry, false); return; }
  if (!entry.loaded) entry.pending.push(action);
  else entry.version++;
  notify(entry);
  if (entry.loaded) void saveEntry(entry).catch(report);
}

export function startEntry<T>(entry: Entry<T>): void {
  void loadEntry(entry).catch(report);
}

export async function retryPendingState(): Promise<void> {
  try {
    await Promise.all([...entries.values()].map(async (entry) => {
      await loadEntry(entry);
      await saveEntry(entry);
    }));
  } catch (error) { report(error); throw error; }
}

export async function refreshTimerState(): Promise<void> {
  const entry = [...entries.values()].find((item) => item.active && item.key === "study-timer");
  if (!entry?.loaded) return;
  await saveEntry(entry);
  const version = entry.version;
  const fresh = await getTimer();
  if (entry.active && entry.version === version) { entry.value = fresh; notify(entry); }
}

export function discardUserState(): void {
  invalidateApiRequests();
  entries.forEach((entry) => { entry.active = false; });
  entries.clear();
}

export function resetWorkspace(resetRequest: () => Promise<unknown>): Promise<void> {
  if (resetPromise) return resetPromise;
  resetPromise = performReset(resetRequest).finally(() => { resetPromise = null; });
  return resetPromise;
}

async function performReset(resetRequest: () => Promise<unknown>): Promise<void> {
  resetting = true;
  window.dispatchEvent(new CustomEvent("studyflow-reset-state", { detail: true }));
  try {
    // Drain pending saves before reset and reject new writes until it finishes.
    await Promise.allSettled([...entries.values()].flatMap((entry) =>
      [entry.loading, entry.saving].filter((promise) => promise !== undefined)));
    for (const entry of entries.values()) {
      if (entry.active && entry.key === "settings" && entry.loaded && entry.savedVersion < entry.version) {
        entry.value = await persist(entry.key, entry.value);
        entry.savedVersion = entry.version;
        notify(entry);
      }
    }
    await resetRequest();
    try {
      const owners = new Set([...entries.values()].map((entry) => entry.cacheKey.split(":")[1]));
      Object.keys(localStorage).filter((key) => [...owners].some((owner) => key.startsWith(`user:${owner}:note-draft:`))).forEach((key) => localStorage.removeItem(key));
    } catch { /* A blocked device cache cannot roll back a completed server reset. */ }
    entries.forEach((entry) => {
      if (entry.key === "settings") return;
      entry.value = entry.key === "study-timer" ? { ...DEFAULT_TIMER_STATE } : [];
      entry.pending = [];
      entry.version = entry.savedVersion = 0;
      entry.loaded = true;
      notify(entry);
    });
    window.dispatchEvent(new Event("studyflow-data-saved"));
  } finally {
    resetting = false;
    window.dispatchEvent(new CustomEvent("studyflow-reset-state", { detail: false }));
  }
}
