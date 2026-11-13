"use client";

import useUserState from "./useUserState";
import { DEFAULT_SETTINGS } from "@/utils/settingsState";
import { StudyFlowSettings } from "@/types/settings";
import { TimerMode } from "@/types/timer";

export default function usePreferences() {
  const [settings, setSettings, state] = useUserState<StudyFlowSettings>("settings", DEFAULT_SETTINGS);
  const durations: Record<TimerMode, number> = { Pomodoro: settings.focusMinutes * 60, "Short Break": settings.shortBreakMinutes * 60, "Long Break": settings.longBreakMinutes * 60 };
  return { settings, setSettings, ready: state.loaded, durations };
}
