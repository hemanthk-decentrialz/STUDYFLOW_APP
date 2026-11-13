"use client";

import usePreferences from "@/hooks/usePreferences";
import { calendarDate } from "@/utils/formatDate";
import { useState } from "react";
import {
  Priority,
  StudySession,
} from "@/types/planner";
import Button from "@/components/ui/Button";
import Card from "@/components/ui/Card";
import { CourseSelect, GoalSelect } from "@/components/ui/StudyLinks";

type PlannerFormProps = {
  onAddSession: (session: StudySession) => Promise<void>;
  initialCourseId?: number;
  initialGoalId?: number;
};

export default function PlannerForm({
  onAddSession, initialCourseId, initialGoalId,
}: PlannerFormProps) {
  const { settings } = usePreferences();
  const [dateDraft, setScheduledDate] = useState<string | null>(null);
  const scheduledDate = dateDraft ?? calendarDate(new Date(), settings.timeZone);
  const [courseId, setCourseId] = useState<number | null>(initialCourseId ?? null);
  const [goalId, setGoalId] = useState<number | null>(initialGoalId ?? null);
  const [subject, setSubject] =
    useState("");

  const [time, setTime] =
    useState("");

  const [durationMinutes, setDurationMinutes] =
    useState(60);

  const [priority, setPriority] =
    useState<Priority>("Medium");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  async function handleSubmit(
    e: React.FormEvent<HTMLFormElement>
  ) {
    e.preventDefault();
    setError("");

    if (!courseId) {
      setError("Choose a course before adding a session.");
      return;
    }

    if (!time) {
      setError("Choose a study start time.");
      return;
    }

    if (
      !Number.isFinite(durationMinutes) ||
      durationMinutes < 15
    ) {
      setError("Duration must be at least 15 minutes.");
      return;
    }

    const newSession: StudySession = {
      id: Date.now(),
      subject,
      courseId: courseId!,
      goalId,
      scheduledDate,
      time,
      durationMinutes,
      priority,
      completed: false,
    };

    setSaving(true);
    try { await onAddSession(newSession); } catch (error) {
      setError(error instanceof Error ? error.message : "Unable to create study session. Your form is kept.");
      return;
    } finally { setSaving(false); }

    setGoalId(null);
    setTime("");
    setDurationMinutes(60);
    setPriority("Medium");
  }

  return (
    <Card className="form-panel planner-form">
      <h2
        className="mb-6 text-2xl font-bold"
        style={{
          color: "var(--foreground)",
        }}
      >
        Add Study Session
      </h2>

      <form
        onSubmit={handleSubmit}
        onChange={() => setError("")}
        aria-describedby={error ? "planner-form-error" : undefined}
        className="planner-fields"
      >
        <label className="block">
          <span className="text-muted mb-2 block text-sm font-medium">Study date</span>
          <input type="date" required value={scheduledDate} onChange={(e) => setScheduledDate(e.target.value)} className="input-theme w-full rounded-lg p-3" />
        </label>
        <CourseSelect required value={courseId} selectedLabel={subject} onChange={(id, title) => { setCourseId(id); setSubject(title); setGoalId(null); }} />
        {courseId && <GoalSelect courseId={courseId} value={goalId} onChange={setGoalId} />}


        <label className="block">
          <span className="text-muted mb-2 block text-sm font-medium">
            Study Time
          </span>

          <input
            required
            type="time"
            value={time}
            onChange={(e) =>
              setTime(e.target.value)
            }
            className="input-theme w-full rounded-lg p-3"
          />
        </label>

        <label className="block">
          <span className="text-muted mb-2 block text-sm font-medium">
            Duration
          </span>

          <input
            type="number"
            required
            max={2147483647}
            min={15}
            step={15}
            value={durationMinutes}
            onChange={(e) =>
              setDurationMinutes(
                Number(e.target.value)
              )
            }
            className="input-theme w-full rounded-lg p-3"
            aria-label="Duration in minutes"
            placeholder="Duration in minutes"
          />
        </label>

        <label className="block">
          <span className="text-muted mb-2 block text-sm font-medium">
            Priority
          </span>

          <select
            value={priority}
            onChange={(e) =>
              setPriority(
                e.target.value as Priority
              )
            }
            className="input-theme w-full rounded-lg p-3"
          >
            <option>High</option>
            <option>Medium</option>
            <option>Low</option>
          </select>
        </label>

        {error && <p id="planner-form-error" role="alert" className="feedback-error">{error}</p>}
        <Button type="submit" disabled={saving} loading={saving}>
          Add Session
        </Button>
      </form>
    </Card>
  );
}
