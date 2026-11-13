"use client";

import { useEffect } from "react";
import useUserState from "@/hooks/useUserState";
import { TimerState } from "@/types/timer";
import {
  DEFAULT_TIMER_STATE,
  getUpdatedTimerState,
} from "@/utils/timerState";

export default function TimerTicker() {
  const [timer, setTimer] =
    useUserState<TimerState>(
      "study-timer",
      DEFAULT_TIMER_STATE
    );

  useEffect(() => {
    if (!timer.isRunning) {
      return;
    }

    function syncTimer() {
      setTimer((previous) =>
        getUpdatedTimerState(previous)
      );
    }

    syncTimer();

    const interval = window.setInterval(
      syncTimer,
      1000
    );

    return () =>
      window.clearInterval(interval);
  }, [timer.isRunning, setTimer]);

  return null;
}
