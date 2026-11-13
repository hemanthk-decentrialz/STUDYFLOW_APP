"use client";

import usePreferences from "@/hooks/usePreferences";
import { formatClock } from "@/utils/formatDate";
import FocusHistory from "@/components/timer/FocusHistory";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import useDashboardData from "@/hooks/useDashboardData";
import useTimer from "@/hooks/useTimer";
import Button from "@/components/ui/Button";
import FullPageLoader from "@/components/ui/FullPageLoader";

function calendarLabel(value: string) {
  return new Date(`${value}T12:00:00`).toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" });
}

export default function Dashboard() {
  const { settings } = usePreferences();
  const { summary, isLoading, error, retry } = useDashboardData();
  const { timer, startFocus } = useTimer();
  const router = useRouter();
  const [starting, setStarting] = useState(false);
  const [startError, setStartError] = useState<string | null>(null);
  async function handleStart() {
    setStarting(true); setStartError(null);
    try { await startFocus(summary?.nextSession?.courseId); router.push("/timer"); }
    catch (failure) { setStartError(failure instanceof Error ? failure.message : "Unable to start. Please try again."); }
    finally { setStarting(false); }
  }
  if (error && !summary) return <div role="alert"><p>{error}</p><button onClick={retry}>Retry loading dashboard</button></div>;
  if (isLoading || !summary) return <FullPageLoader label="Loading today..." />;
  const next = summary.nextSession;
  return <div className="today-workspace">
    <header className="today-heading"><div><p className="today-eyebrow">YOUR DAY, AT A GLANCE</p><h1>Today</h1><p className="text-muted">{calendarLabel(summary.date)} · {summary.timeZone.replaceAll("_", " ")}</p></div></header>
    {error && <p role="alert">{error} <button onClick={retry}>Retry refreshing</button></p>}
    <section className="today-focus" aria-labelledby="focus-heading">
      <div><p className="today-eyebrow">{timer.isRunning ? "TIMER IN PROGRESS" : "NEXT STUDY SESSION"}</p>
        <h2 id="focus-heading">{timer.isRunning ? "Keep your momentum." : next?.subject ?? "Make room for focused study."}</h2>
        <p className="text-muted">{next ? `${timer.isRunning ? `Next planned: ${next.subject} · ` : ""}${calendarLabel(next.scheduledDate!)} · ${formatClock(next.time, settings.timeFormat)} · ${next.durationMinutes} min planned` : "Choose a subject and a time in your planner, or start a focus block now."}</p>
        {next && <div className="course-links"><Link href={`/notes?course_id=${next.courseId}`}>Open course notes</Link>{next.goalId && <Link href={`/goals?course_id=${next.courseId}&goal_id=${next.goalId}`}>View linked goal</Link>}</div>}
        <p className="today-focus-note">{timer.isRunning ? "Your current timer will continue without being reset." : `Start a ${settings.focusMinutes}-minute focus block, or resume your paused focus timer. Your planned session stays unchanged.`}</p>
      </div><div className="today-start"><Button loading={starting} onClick={handleStart}>{timer.isRunning ? "Open running timer" : "Start studying"}</Button>{startError && <p role="alert">{startError}</p>}</div>
    </section>
    {summary.undatedPlannerCount > 0 && <p className="today-notice">{summary.undatedPlannerCount} older session{summary.undatedPlannerCount === 1 ? " is" : "s are"} unscheduled. <Link href="/planner">Assign dates in Planner</Link> to include them here.</p>}
    <div className="today-columns">
      <section className="today-section" aria-labelledby="agenda-heading">
        <div className="today-section-heading"><h2 id="agenda-heading">Today’s plan</h2><span>{summary.todayCompletedCount}/{summary.todaySessionCount} complete</span></div>
        <p className="text-muted text-sm mb-5">{summary.todayPlannedMinutes} minutes planned · Your calendar day</p>
        {summary.todaySessions.length ? <ol className="today-list">{summary.todaySessions.map((session) => <li key={session.id}><time>{formatClock(session.time, settings.timeFormat)}</time><div><strong className={session.completed ? "line-through text-muted" : ""}>{session.subject}</strong><p>{session.durationMinutes} min · {session.completed ? "Completed" : session.priority + " priority"}</p></div><span className="today-status" aria-label={session.completed ? "Completed" : "Planned"}>{session.completed ? "✓" : "—"}</span></li>)}</ol> : <div className="today-empty"><h3>A little space to plan.</h3><p>No sessions scheduled for today. Choose a subject and a time that works for you.</p><Link href="/planner">Add a session</Link></div>}
        {summary.todaySessionCount > summary.todaySessions.length && <Link className="today-footer-link" href="/planner">View all sessions</Link>}
      </section>
      <section className="today-section" aria-labelledby="deadlines-heading">
        <div className="today-section-heading"><h2 id="deadlines-heading">Coming up</h2><span>Next 7 days</span></div>
        {summary.overdueGoalCount > 0 && <p className="today-notice">{summary.overdueGoalCount} unfinished goals are overdue.</p>}
        {summary.upcomingGoals.length ? <ol className="today-list">{summary.upcomingGoals.map((goal) => <li key={goal.id}><div><strong>{goal.title}</strong><p>Due {calendarLabel(goal.deadline)} · {goal.progress}% complete</p></div></li>)}</ol> : <div className="today-empty"><h3>No deadlines on the horizon.</h3><p>Unfinished goals due in the next seven days will appear here.</p></div>}
        <Link className="today-footer-link" href="/goals">{summary.overdueGoalCount > 0 ? "Review goals" : "View goals"}</Link>
      </section>
    </div>
    <FocusHistory compact />
    <section className="today-overview" aria-labelledby="overview-heading"><h2 id="overview-heading">Your study space <span>All time</span></h2><dl>
      <div><dt>Sessions completed</dt><dd>{summary.completedPlanner}<small> of {summary.plannerCount} planned</small></dd></div>
      <div><dt>Notes saved</dt><dd>{summary.totalNotes}</dd></div>
      <div><dt>Goals completed</dt><dd>{summary.completedGoals}<small> of {summary.totalGoals}</small></dd></div>
      <div><dt>Pomodoros completed</dt><dd>{summary.totalSessions}</dd></div>
    </dl></section>
  </div>;
}
