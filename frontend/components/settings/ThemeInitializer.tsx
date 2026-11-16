"use client";

import { useLayoutEffect } from "react";
import useUserState from "@/hooks/useUserState";
import { getStorageItem, setStorageItem } from "@/lib/storage";
import { StudyFlowSettings } from "@/types/settings";
import { DEFAULT_SETTINGS } from "@/utils/settingsState";

export default function ThemeInitializer() {
  const [settings] = useUserState<StudyFlowSettings>("settings", {
    ...DEFAULT_SETTINGS,
    theme: getStorageItem<string>("theme", "light") === "dark" ? "dark" : "light",
  });
  useLayoutEffect(() => {
    document.documentElement.classList.remove("light", "dark");
    document.documentElement.classList.add(settings.theme);
    setStorageItem("theme", settings.theme);
  }, [settings.theme]);
  return null;
}
