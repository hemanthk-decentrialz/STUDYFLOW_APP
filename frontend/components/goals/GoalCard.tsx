"use client";

import Link from "next/link";
import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";
import ProgressBar from "./ProgressBar";
import { Goal } from "@/types/goal";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faTrash, faBookOpen, faCalendarDays, faCheckCircle } from "@fortawesome/free-solid-svg-icons";

interface GoalCardProps {
  goal: Goal;
  onProgressChange: (id: number, progress: number) => void;
  onDelete: (id: number) => void;
}

export default function GoalCard({ goal, onProgressChange, onDelete }: GoalCardProps) {
  const completed = goal.progress >= 100;
  return <Card className="goal-card">
    <div className="goal-subject"><FontAwesomeIcon icon={faBookOpen} aria-hidden="true" />{goal.subject}</div>
    <h2>{goal.title}</h2>
    {completed && <span className="goal-complete"><FontAwesomeIcon icon={faCheckCircle} aria-hidden="true" />Completed</span>}
    <p className="goal-deadline"><FontAwesomeIcon icon={faCalendarDays} aria-hidden="true" />Due <time dateTime={goal.deadline}>{goal.deadline}</time></p>
    <ProgressBar progress={goal.progress} />
    <label className="goal-manual">Set manual progress<input type="range" min={0} max={100} step={10} value={goal.progress} onChange={(event) => onProgressChange(goal.id, Number(event.target.value))} aria-label={`Progress for ${goal.title}`} /></label>
    <p className="goal-contributions">{goal.completedSessionCount ?? 0} of {goal.linkedSessionCount ?? 0} linked sessions complete.</p>
    <div className="course-links"><Link href={`/planner?course_id=${goal.courseId}&goal_id=${goal.id}`}>Linked sessions</Link><Link href={`/notes?course_id=${goal.courseId}`}>Course notes</Link></div>
    <div className="goal-actions"><Button variant="danger" onClick={() => onDelete(goal.id)}><FontAwesomeIcon icon={faTrash} aria-hidden="true" />Delete</Button></div>
  </Card>;
}
