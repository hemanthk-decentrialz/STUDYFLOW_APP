"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { ResourceQuery } from "@/lib/api/resources";

import PlannerCard from "@/components/planner/PlannerCard";
import PlannerForm from "@/components/planner/PlannerForm";
import ResourceControls from "@/components/ui/ResourceControls";
import useResourceList from "@/hooks/useResourceList";
import { plannerApi } from "@/lib/api/resources";
import { StudySession } from "@/types/planner";

function PlannerPageContent({ initialQuery }: { initialQuery: ResourceQuery }) {
  const resources = useResourceList(plannerApi, initialQuery);
  const addSession = async (session: StudySession) => { await resources.create(session); };
  const deleteSession = (id: number) => { void resources.remove(id).catch(() => { }); };
  const toggleSession = (id: number) => {
    const session = resources.items.find((item) => item.id === id);
    if (session) void resources.patch(id, { completed: !session.completed }).catch(() => { });
  };
  return <div>
    <ResourceControls title="Study planner" description="Organize your study sessions and track completion." module="planner" query={resources.query} data={resources.data}
      onChange={resources.setQuery} loading={resources.loading} error={resources.error} retry={resources.retry} />
    <div className="workspace-grid">
      <PlannerForm initialGoalId={resources.query.goal_id} initialCourseId={resources.query.course_id} onAddSession={addSession} />
      <fieldset disabled={resources.loading} className="planner-list">
        {!resources.loading && !resources.items.length && <p>No sessions in this view. Adjust your filters or plan a dated session using the form.</p>}
        {resources.items.map((session) => <PlannerCard key={session.id} session={session}
          onDelete={deleteSession} onToggle={toggleSession} onGoal={(id, goalId) => { void resources.patch(id, { goalId }).catch(() => { }); }} onSchedule={(id, date) => { void resources.patch(id, { scheduledDate: date }).catch(() => { }); }} />)}
      </fieldset>
    </div>
  </div>;
}

function LinkedPage() {
  const params = useSearchParams();
  const parseId = (name: string) => { const value = Number(params.get(name)); return Number.isSafeInteger(value) && value > 0 ? value : undefined; };
  const initialQuery: ResourceQuery = { course_id: parseId("course_id"), goal_id: parseId("goal_id") };
  return <PlannerPageContent key={params.toString()} initialQuery={initialQuery} />;
}
export default function PlannerPage() { return <Suspense fallback={<p role="status">Loading study workspace...</p>}><LinkedPage /></Suspense>; }
