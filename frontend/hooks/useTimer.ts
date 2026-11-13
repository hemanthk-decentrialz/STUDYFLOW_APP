"use client";

import { retryPendingState } from "@/lib/api/state";
import useUserState from "./useUserState";

import usePreferences from "./usePreferences";
import { TimerMode, TimerState } from "@/types/timer";
import { formatTime } from "@/utils/formatTime";
import {
  DEFAULT_TIMER_STATE,
} from "@/utils/timerState";

export default function useTimer() {
  const { durations } = usePreferences();
  const [timer, setTimer] = useUserState<TimerState>(
    "study-timer",
    DEFAULT_TIMER_STATE
  );

  async function startFocus(courseId?: number | null) {
    await retryPendingState();
    setTimer((previous) => {
      if (previous.isRunning) return previous;
      const timeLeft = previous.mode === "Pomodoro" && previous.timeLeft > 0 ? previous.timeLeft : durations.Pomodoro;
      return { ...previous, courseId: courseId === undefined ? previous.courseId : courseId, mode: "Pomodoro", timeLeft, isRunning: true, endAt: Date.now() + timeLeft * 1000 };
    });
    await retryPendingState();
  }

  function startTimer() {
    setTimer((previous) => ({
      ...previous,
      timeLeft:
        previous.timeLeft > 0
          ? previous.timeLeft
          : durations[previous.mode],
      isRunning: true,
      endAt:
        Date.now() +
        (previous.timeLeft > 0
          ? previous.timeLeft
          : durations[previous.mode]) *
          1000,
    }));
  }

  function pauseTimer() {
    setTimer((previous) => {
      const timeLeft =
        previous.endAt && previous.isRunning
          ? Math.max(
              0,
              Math.ceil(
                (previous.endAt - Date.now()) /
                  1000
              )
            )
          : previous.timeLeft;

      return {
        ...previous,
        timeLeft,
        isRunning: false,
        endAt: undefined,
      };
    });
  }

  function resetTimer() {
    setTimer((previous) => ({
      ...previous,
      isRunning: false,
      timeLeft: durations[previous.mode],
      endAt: undefined,
    }));
  }

  function changeMode(mode: TimerMode) {
    setTimer((previous) => ({
      ...previous,
      mode,
      timeLeft: durations[mode],
      isRunning: false,
      endAt: undefined,
    }));
  }

  return {
    timer, durations,
    setCourse: (courseId: number | null) => setTimer((previous) => ({ ...previous, courseId })),
    startTimer,
    startFocus,
    pauseTimer,
    resetTimer,
    changeMode,
    formatTime,
  };
}
