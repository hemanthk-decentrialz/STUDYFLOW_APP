"use client";

import usePreferences from "@/hooks/usePreferences";
import { formatDateTime } from "@/utils/formatDate";
import { useEffect, useState } from "react";
import { getFocusHistory, getFocusSummary } from "@/lib/api/timer";
import { ResourcePage } from "@/lib/api/resources";
import { FocusSession, FocusSummary } from "@/types/timer";
import { CourseSelect } from "@/components/ui/StudyLinks";

function duration(seconds: number) {
  const minutes = Math.floor(seconds / 60);
  return minutes >= 60 ? `${Math.floor(minutes / 60)}h ${minutes % 60}m` : minutes ? `${minutes}m ${seconds % 60}s` : `${seconds}s`;
}

export default function FocusHistory({ compact = false }: { compact?: boolean }) {
  const { settings } = usePreferences();
  const [summary, setSummary] = useState<FocusSummary | null>(null);
  const [history, setHistory] = useState<ResourcePage<FocusSession> | null>(null);
  const [courseId, setCourseId] = useState<number | null | undefined>(undefined);
  const [page, setPage] = useState(1);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    let inFlight = false, queued = false;
    const load = async () => {
      if (inFlight) { queued = true; return; }
      inFlight = true;
      setLoading(true);
      try {
        const [totals, records] = await Promise.all([getFocusSummary(settings.timeZone, controller.signal), compact || courseId === undefined ? Promise.resolve(null) : getFocusHistory(page, courseId ?? undefined, controller.signal)]);
        if (!controller.signal.aborted) { setSummary(totals); setHistory(records); setError(""); }
      } catch (failure) { if (!controller.signal.aborted) setError(failure instanceof Error ? failure.message : "Unable to load focus history."); }
      finally { inFlight = false; if (!controller.signal.aborted) { setLoading(false); if (queued) { queued = false; void load(); } } }
    };
    void load();
    let timeout: ReturnType<typeof setTimeout>;
    const refresh = () => { clearTimeout(timeout); timeout = setTimeout(() => { void load(); }, 200); };
    const interval = setInterval(() => { if (document.visibilityState === "visible") refresh(); }, 30_000);
    window.addEventListener("studyflow-data-saved", refresh); window.addEventListener("focus", refresh);
    return () => { controller.abort(); clearTimeout(timeout); clearInterval(interval); window.removeEventListener("studyflow-data-saved", refresh); window.removeEventListener("focus", refresh); };
  }, [compact, courseId, page, revision, settings.timeZone, settings.weekStartsOn]);
  const maximum = Math.max(1, ...(summary?.days.map((day) => day.seconds) ?? [1]));
  return <section className="focus-history" aria-labelledby={compact ? "focus-week-dashboard" : "focus-week-timer"}>
    <div className="today-section-heading"><h2 id={compact ? "focus-week-dashboard" : "focus-week-timer"}>Focus this week</h2>{loading && <span role="status">Updating…</span>}</div>
    {error && <p role="alert" className="feedback-error">{error} <button onClick={() => setRevision((value) => value + 1)}>Retry history</button></p>}
    {summary && <><p className="text-muted text-sm">Week of {summary.weekStart} · {summary.timeZone} · {summary.completedPomodoros} {summary.completedPomodoros === 1 ? "Pomodoro" : "Pomodoros"} completed</p><p className="focus-summary-total">{duration(summary.seconds)}</p>
      <div className="focus-summary-layout"><div className="focus-days" aria-label="Focus time by day">{summary.days.map((day) => <div key={day.date}><span>{duration(day.seconds)}</span><div className="focus-day-track"><div style={{ height: `${Math.max(day.seconds ? 3 : 0, day.seconds / maximum * 100)}%` }} /></div><time dateTime={day.date}>{new Date(`${day.date}T12:00:00`).toLocaleDateString(undefined, { weekday: "short" })}</time></div>)}</div>
        <div className="focus-summary-courses"><h3>Course attention <span className="text-muted text-xs">Top 20 this week</span></h3>
          {summary.courses.length ? <ul className="focus-courses">{summary.courses.map((course) => <li key={`${course.courseId}:${course.title}`}><span>{course.title}</span><strong>{duration(course.seconds)}</strong></li>)}</ul> : <p className="text-muted text-sm">Start a focus timer to build a real history. Older timer counters are not converted into study time.</p>}</div></div>
    </>}
    {!compact && <><div className="mt-8 max-w-md"><CourseSelect label="History course filter" placeholder="Select the course" emptyLabel="All courses" completedFocusOnly value={courseId} selectedLabel={courseId === undefined ? "Select the course" : courseId === null ? "All courses" : undefined} onReset={() => { setCourseId(undefined); setPage(1); setHistory(null); setError(""); setRevision((value) => value + 1); }} onChange={(id) => { setCourseId(id); setPage(1); setHistory(null); setError(""); setRevision((value) => value + 1); }} /></div>{courseId !== undefined && <><h3 className="font-semibold mt-6 mb-3">Focus intervals</h3><p className="text-muted text-xs mb-4">Pausing ends an interval. Resuming starts another. Breaks are excluded; partial focus time is retained.</p>
      <ul className="focus-intervals">{history?.items.map((record) => <li key={record.id}><div><strong>{record.courseTitle}</strong><p>{formatDateTime(record.startedAt, settings)} · {record.outcome}</p></div><span>{duration(record.seconds)}</span></li>)}</ul>
      {!loading && history?.total === 0 && <p className="text-muted">No focus intervals match this view.</p>}
      {history && history.total_pages > 1 && <div className="resource-pagination mt-5 text-sm"><button disabled={loading || page <= 1} onClick={() => setPage((value) => value - 1)}>Previous</button><span>{page} / {history.total_pages}</span><button disabled={loading || page >= (history?.total_pages ?? 0) || page * 10 > 10000} onClick={() => setPage((value) => value + 1)}>Next</button></div>}
    </>}</>}
  </section>;
}
