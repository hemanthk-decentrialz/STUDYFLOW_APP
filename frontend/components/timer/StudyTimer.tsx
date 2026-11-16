"use client";

import Link from "next/link";
import { CourseSelect } from "@/components/ui/StudyLinks";
import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";
import useTimer from "@/hooks/useTimer";
import { TimerMode } from "@/types/timer";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faPlay, faPause, faRotateLeft } from "@fortawesome/free-solid-svg-icons";

export default function StudyTimer() {
  const { timer, durations, setCourse, startTimer, pauseTimer, resetTimer, changeMode, formatTime } = useTimer();
  const status = timer.isRunning ? "Session in progress" : timer.timeLeft === 0 ? "Session complete" : timer.timeLeft < timer.blockDuration ? "Paused. Pick up where you left off." : "Ready when you are.";
  return <Card className="timer-workspace">
    <div className="timer-toolbar"><CourseSelect emptyLabel="Unassigned" label="Focus course" value={timer.courseId} onChange={setCourse} disabled={timer.isRunning} /><p>Durations and sound live in <Link className="text-(--primary)" href="/settings#focus-preferences">Settings</Link>.</p></div>
    <div className="timer-modes" role="group" aria-label="Timer mode">{(Object.keys(durations) as TimerMode[]).map((mode) => <button type="button" key={mode} aria-pressed={timer.mode === mode} onClick={() => changeMode(mode)}><span>{mode}</span><small>{durations[mode] / 60} min</small></button>)}</div>
    <div className="timer-display"><p>{timer.mode}</p><output role="timer" aria-live="off" aria-label={`${timer.mode} time remaining`}>{formatTime(timer.timeLeft)}</output><p>{status}</p></div>
    <div className="timer-actions"><Button onClick={startTimer} disabled={timer.isRunning}><FontAwesomeIcon icon={faPlay} aria-hidden="true" />Start</Button><Button variant="secondary" onClick={pauseTimer} disabled={!timer.isRunning}><FontAwesomeIcon icon={faPause} aria-hidden="true" />Pause</Button><Button variant="secondary" onClick={resetTimer}><FontAwesomeIcon icon={faRotateLeft} aria-hidden="true" />Reset</Button></div>
    <p className="timer-footnote">{timer.completedSessions} Pomodoros completed · All time<br /><span className="inline-block mt-2">History includes sessions recorded since focus tracking began.</span></p>
  </Card>;
}
