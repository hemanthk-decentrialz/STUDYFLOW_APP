"use client";

import { Dispatch, SetStateAction, useCallback, useEffect, useMemo, useState, useSyncExternalStore } from "react";
import { useAuth } from "@/context/AuthContext";
import { getEntry, startEntry, updateEntry } from "@/lib/api/state";

export default function useUserState<T>(key: string, initialValue: T) {
  const { user, isLoading } = useAuth();
  const [initial] = useState(() => initialValue);
  const entry = useMemo(() => user && !isLoading
    ? getEntry(user.id, key, initial) : null, [user, isLoading, key, initial]);
  const subscribe = useCallback((listener: () => void) => {
    if (!entry) return () => { };
    entry.listeners.add(listener);
    return () => { entry.listeners.delete(listener); };
  }, [entry]);
  const snapshot = useCallback(() => entry?.value ?? initial, [entry, initial]);
  const serverSnapshot = useCallback(() => initial, [initial]);
  const value = useSyncExternalStore(subscribe, snapshot, serverSnapshot);
  useEffect(() => { if (entry) startEntry(entry); }, [entry]);
  const setValue: Dispatch<SetStateAction<T>> = useCallback((action) => {
    if (entry) updateEntry(entry, action);
  }, [entry]);
  return [value, setValue, { loaded: entry?.loaded ?? false }] as const;
}
