"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, ReactNode } from "react";
import { AUTH_EVENT_KEY, announceAuthChange, canResumeSession, getSession, saveSession, clearSession } from "@/lib/auth";
import { getCurrentUser, logout as logoutRequest, updateProfile as saveProfile } from "@/lib/api/auth";
import { discardUserState } from "@/lib/api/state";
import { SessionUser } from "@/types/auth";

interface AuthContextType {
  user: SessionUser | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (user: SessionUser) => Promise<void>;
  logout: () => Promise<void>;
  updateProfile: (name: string) => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<SessionUser | null>(null);
  const [isLoading, setLoading] = useState(true);
  const generation = useRef(0);

  const forgetSession = useCallback(() => {
    ++generation.current;
    discardUserState();
    clearSession();
    setUser(null);
    setLoading(false);
  }, []);

  useEffect(() => {
    const version = ++generation.current;
    let active = true;
    const expected = getSession();
    const resume = canResumeSession();
    const expired = () => { if (active) forgetSession(); };
    const changedElsewhere = (event: StorageEvent) => {
      if (event.key === AUTH_EVENT_KEY || event.key === null) expired();
    };
    const restored = (event: PageTransitionEvent) => { if (event.persisted) expired(); };
    window.addEventListener("studyflow-session-expired", expired);
    window.addEventListener("storage", changedElsewhere);
    window.addEventListener("pageshow", restored);

    // Defer state changes so Strict Mode can dispose its first mount safely.
    void (async () => {
      await Promise.resolve();
      if (!active || version !== generation.current) return;
      if (!resume || !expected) { forgetSession(); return; }
      try {
        const current = await getCurrentUser();
        if (!active || version !== generation.current) return;
        if (current.id !== expected.id) { forgetSession(); return; }
        saveSession(current);
        setUser(current);
      } catch {
        if (active && version === generation.current) forgetSession();
      } finally {
        if (active && version === generation.current) setLoading(false);
      }
    })();
    return () => {
      active = false;
      window.removeEventListener("studyflow-session-expired", expired);
      window.removeEventListener("storage", changedElsewhere);
      window.removeEventListener("pageshow", restored);
    };
  }, [forgetSession]);

  const login = useCallback(async (expected: SessionUser) => {
    const version = ++generation.current;
    discardUserState();
    setLoading(true);
    try {
      const current = await getCurrentUser();
      if (version !== generation.current) throw new Error("Your sign-in changed. Please try again.");
      if (current.id !== expected.id) throw new Error("Login session could not be verified.");
      saveSession(current);
      setUser(current);
      announceAuthChange();
    } catch (error) {
      if (version === generation.current) forgetSession();
      throw error;
    } finally {
      if (version === generation.current) setLoading(false);
    }
  }, [forgetSession]);

  const logout = useCallback(async () => {
    const version = ++generation.current;
    await logoutRequest();
    if (version !== generation.current) return;
    forgetSession();
    announceAuthChange();
  }, [forgetSession]);

  const updateProfile = useCallback(async (name: string) => {
    const version = generation.current;
    const current = await saveProfile({ name });
    if (version !== generation.current || current.id !== user?.id) {
      throw new Error("Your sign-in changed. Please sign in again.");
    }
    saveSession(current);
    setUser(current);
  }, [user?.id]);

  const value = useMemo(() => ({ user, isLoading, isAuthenticated: !!user, login, logout, updateProfile }),
    [user, isLoading, login, logout, updateProfile]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider.");
  return context;
}
