"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import Button from "@/components/ui/Button";
import Card from "@/components/ui/Card";
import ResourceControls from "@/components/ui/ResourceControls";
import useResourceList from "@/hooks/useResourceList";
import { courseApi } from "@/lib/api/resources";
import { Course } from "@/types/course";

function CourseCard({ course, onSave, onDelete, disabled }: {
  course: Course; onSave: (id: number, changes: Partial<Course>) => Promise<unknown>;
  onDelete: (id: number) => Promise<unknown>; disabled: boolean;
}) {
  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState(course.title);
  const [description, setDescription] = useState(course.description);
  return <Card className="course-card"><div className="flex justify-between items-start gap-4"><div><p className="today-eyebrow mb-2">COURSE</p><h2 className="text-xl font-semibold break-words">{course.title}</h2></div><button className="text-sm text-(--primary)" disabled={disabled} onClick={() => { setTitle(course.title); setDescription(course.description); setEditing(!editing); }}>{editing ? "Cancel" : "Edit"}</button></div>
    {editing ? <form className="space-y-3 mt-5" onSubmit={async (event) => { event.preventDefault(); try { await onSave(course.id, { title, description }); setEditing(false); } catch { /* Shared resource feedback displays the failure. */ } }}>
      <label className="block text-sm">Course name<input required maxLength={200} className="input-theme w-full rounded-lg p-3 mt-2" value={title} onChange={(event) => setTitle(event.target.value)} /></label>
      <label className="block text-sm">Description<textarea maxLength={2000} className="input-theme w-full rounded-lg p-3 mt-2" value={description} onChange={(event) => setDescription(event.target.value)} /></label>
      <Button type="submit" disabled={disabled}>Save course</Button>
    </form> : <p className="text-muted text-sm mt-3 whitespace-pre-wrap break-words">{course.description || "Your sessions, notes and goals, together."}</p>}
    <div className="course-links"><Link href={`/planner?course_id=${course.id}`}>Plan sessions ↗</Link><Link href={`/notes?course_id=${course.id}`}>Open notes ↗</Link><Link href={`/goals?course_id=${course.id}`}>View goals ↗</Link></div>
    <button className="text-xs text-muted mt-5" disabled={disabled} onClick={() => { void onDelete(course.id).catch(() => { }); }}>Remove empty course</button>
  </Card>;
}

export default function CoursesPage() {
  const resources = useResourceList(courseApi);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  async function create(event: FormEvent) {
    event.preventDefault();
    try { await resources.create({ id: Date.now(), title, description }); setTitle(""); setDescription(""); } catch { /* Shared feedback retains the draft. */ }
  }
  return <div>
    <ResourceControls title="Courses" description="One home for each subject you study. Connect its sessions, notes and goals." module="courses" query={resources.query} data={resources.data} onChange={resources.setQuery} loading={resources.loading} error={resources.error} retry={resources.retry} />
    <div className="workspace-grid"><Card className="form-panel"><h2 className="text-lg font-semibold mb-5">Add a course</h2><form className="space-y-4" onSubmit={create}>
      <label className="block text-sm">Course name<input required maxLength={200} value={title} onChange={(event) => setTitle(event.target.value)} placeholder="e.g. Calculus II" className="input-theme w-full rounded-lg p-3 mt-2" /></label>
      <label className="block text-sm">Description <span className="text-muted">(optional)</span><textarea maxLength={2000} rows={3} value={description} onChange={(event) => setDescription(event.target.value)} className="input-theme w-full rounded-lg p-3 mt-2" /></label>
      <Button type="submit" disabled={resources.loading}>Create course</Button>
    </form></Card><div className="course-library">
        {!resources.loading && !resources.items.length && <div className="today-empty"><h2 className="font-semibold">Build your study library.</h2><p>Add a course, then plan sessions, collect notes and set goals within it.</p></div>}
        {resources.items.map((course) => <CourseCard key={course.id} course={course} disabled={resources.loading} onSave={resources.patch} onDelete={resources.remove} />)}
      </div></div>
  </div>;
}
