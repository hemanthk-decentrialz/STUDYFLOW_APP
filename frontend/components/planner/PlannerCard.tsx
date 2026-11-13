"use client";

import { useState } from "react";
import Link from "next/link";
import usePreferences from "@/hooks/usePreferences";
import { formatClock } from "@/utils/formatDate";
import { GoalSelect } from "@/components/ui/StudyLinks";
import Card from "@/components/ui/Card";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faTrash, faCheck, faClock, faHourglassHalf } from "@fortawesome/free-solid-svg-icons";
import { StudySession } from "@/types/planner";

type Props = {
  session: StudySession;
  onDelete: (id: number) => void;
  onToggle: (id: number) => void;
  onSchedule: (id: number, date: string) => void;
  onGoal: (id: number, goalId: number | null) => void;
};

export default function PlannerCard({ session, onDelete, onToggle, onSchedule, onGoal }: Props) {
  const [linking, setLinking] = useState(false);
  const { settings } = usePreferences();
  const priorityColor = session.priority === "High" ? "var(--danger-text)" : session.priority === "Medium" ? "var(--warning-text)" : "var(--success-text)";
  return <Card className={`planner-card${session.completed ? " opacity-80" : ""}`}>
    <div className="planner-card-top"><div className="planner-card-title">
      <button type="button" className="planner-complete" aria-pressed={session.completed} aria-label={`${session.completed ? "Mark pending" : "Complete"} ${session.subject}`} onClick={() => onToggle(session.id)}>{session.completed && <FontAwesomeIcon icon={faCheck} aria-hidden="true" />}</button>
      <h2 className={session.completed ? "line-through opacity-60" : undefined}>{session.subject}</h2>
    </div><span className="planner-priority" style={{ color: priorityColor }}>{session.priority} priority</span></div>
    <div className="planner-details"><span><FontAwesomeIcon icon={faClock} aria-hidden="true" />{formatClock(session.time, settings.timeFormat)}</span><span><FontAwesomeIcon icon={faHourglassHalf} aria-hidden="true" />{session.durationMinutes ? `${session.durationMinutes} min` : "Duration not set"}</span>
      <label className="planner-date">{session.scheduledDate ? "Study date" : "Choose a date"}<input type="date" aria-label={`Study date for ${session.subject}`} className="input-theme" value={session.scheduledDate ?? ""} onChange={(event) => { if (event.target.value) onSchedule(session.id, event.target.value); }} /></label>
    </div>
    <button type="button" className="quiet-action" aria-expanded={linking} onClick={() => setLinking(!linking)}>{linking ? "Close goal selector" : session.goalId ? "Change linked goal" : "Link a goal"}</button>
    {linking && <div className="mt-3"><GoalSelect courseId={session.courseId} value={session.goalId} onChange={(goalId) => onGoal(session.id, goalId)} /></div>}
    <div className="planner-footer"><div className="course-links"><Link href={`/notes?course_id=${session.courseId}`}>Course notes</Link>{session.goalId && <Link href={`/goals?course_id=${session.courseId}&goal_id=${session.goalId}`}>Linked goal</Link>}<span className="text-muted">{session.completed ? "Completed" : "Pending"}</span></div>
      <button type="button" className="quiet-action quiet-danger" onClick={() => onDelete(session.id)}><FontAwesomeIcon icon={faTrash} aria-hidden="true" />Delete</button>
    </div>
  </Card>;
}
