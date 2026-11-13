"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { ResourceQuery } from "@/lib/api/resources";

import { useState } from "react";
import GoalCard from "@/components/goals/GoalCard";
import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";
import useResourceList from "@/hooks/useResourceList";
import { goalApi } from "@/lib/api/resources";
import ResourceControls from "@/components/ui/ResourceControls";
import { CourseSelect } from "@/components/ui/StudyLinks";

function GoalsPageContent({ initialQuery }: { initialQuery: ResourceQuery }) {
  const resources = useResourceList(goalApi, initialQuery);
  const goals = resources.items;
  const [courseId, setCourseId] = useState<number | null>(initialQuery.course_id ?? null);
  const [title, setTitle] = useState("");
  const [subject, setSubject] = useState("");
  const [error, setError] = useState("");
  const [deadline, setDeadline] = useState("");

  async function addGoal() {
    setError("");
    if (!title.trim()) {
      setError("Enter a goal title.");
      return;
    }
    if (!courseId) {
      setError("Choose a course.");
      return;
    }
    if (!deadline) {
      setError("Choose a deadline.");
      return;
    }
    try {
      await resources.create({ id: Date.now(), title, subject, courseId: courseId!, deadline, progress: 0 });
    } catch (error) {
      setError(error instanceof Error ? error.message : "Unable to create goal. Your form is kept.");
      return;
    }
    setTitle("");
    setDeadline("");
  }

  function deleteGoal(id: number) {
    void resources.remove(id).catch(() => {});
  }

  function updateProgress(id: number, progress: number) {
    void resources.patch(id, { progress }).catch(() => {});
  }

  return (
    <div>
      <ResourceControls title="Goals" description="Track your study goals and update your progress." module="goals" query={resources.query} data={resources.data}
        onChange={resources.setQuery} loading={resources.loading} error={resources.error} retry={resources.retry} />
      <div className="workspace-grid">
        <Card className="form-panel">
          <h2 className="mb-5 text-2xl font-bold">
            Add Goal
          </h2>
          <form className="space-y-4" onChange={() => setError("")} onSubmit={(event) => { event.preventDefault(); void addGoal(); }} aria-describedby={error ? "goal-form-error" : undefined}>
            <label className="block text-sm"><span className="block mb-2">Goal title</span><input
              required
              aria-label="Goal title"
              type="text"
              placeholder="Goal Title"
              maxLength={200}
              value={title}
              onChange={(e) =>
                setTitle(e.target.value)
              }
              className="input-theme w-full rounded-lg p-3"
            />
            </label>
            <CourseSelect required value={courseId} selectedLabel={subject} onChange={(id, title) => { setCourseId(id); setSubject(title); }} />
            <label className="block text-sm"><span className="block mb-2">Deadline</span><input
              required
              aria-label="Goal deadline"
              type="date"
              value={deadline}
              onChange={(e) =>
                setDeadline(e.target.value)
              }
              className="input-theme w-full rounded-lg p-3"
            />
            </label>
            {error && <p id="goal-form-error" role="alert" className="feedback-error">{error}</p>}
            <Button type="submit" disabled={resources.loading} loading={resources.loading}>
              Add Goal
            </Button>
          </form>
        </Card>
        <fieldset disabled={resources.loading} className="goal-collection">
          {goals.length === 0 ? (
            <Card>
              <p className="text-muted text-center">
                {resources.query.course_id || resources.query.search || resources.query.goal_id ? "No matching goals. Clear filters or add a goal for this course." : "No goals yet. Choose a course and a deadline to create your first goal."}
              </p>
            </Card>
          ) : (
            goals.map((goal) => (
              <GoalCard
                key={goal.id}
                goal={goal}
                onProgressChange={updateProgress}
                onDelete={deleteGoal}
              />
            ))
          )}
        </fieldset>
      </div>
    </div>
  );
}

function LinkedPage() {
  const params = useSearchParams();
  const parseId = (name: string) => { const value = Number(params.get(name)); return Number.isSafeInteger(value) && value > 0 ? value : undefined; };
  const initialQuery: ResourceQuery = { course_id: parseId("course_id"), goal_id: parseId("goal_id") };
  return <GoalsPageContent key={params.toString()} initialQuery={initialQuery} />;
}
export default function GoalsPage() { return <Suspense fallback={<p role="status">Loading study workspace...</p>}><LinkedPage /></Suspense>; }
