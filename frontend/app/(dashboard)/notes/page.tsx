"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { ResourceQuery } from "@/lib/api/resources";

import NoteEditor from "@/components/notes/NoteEditor";
import NoteCard from "@/components/notes/NoteCard";
import ResourceControls from "@/components/ui/ResourceControls";
import useResourceList from "@/hooks/useResourceList";
import { noteApi } from "@/lib/api/resources";
import { NoteInput } from "@/types/note";

function NotesPageContent({ initialQuery }: { initialQuery: ResourceQuery }) {
  const resources = useResourceList(noteApi, initialQuery);
  const addNote = async (note: NoteInput) => resources.create(note);
  const deleteNote = (id: number) => { void resources.remove(id).catch(() => { }); };
  return <div>
    <ResourceControls title="Study notes" description="Read, edit and recover your course notes." module="notes" query={resources.query} data={resources.data}
      onChange={resources.setQuery} loading={resources.loading} error={resources.error} retry={resources.retry} />
    <div className="workspace-grid">
      <NoteEditor initialCourseId={resources.query.course_id} onAddNote={addNote} onSaved={() => resources.retry()} />
      <fieldset disabled={resources.loading} className="notes-list items-start">
        {!resources.loading && !resources.items.length && <p>No notes in this view. Adjust your filters or choose a course and create a note.</p>}
        {resources.items.map((note) => <NoteCard key={note.id} note={note} onDelete={deleteNote} onSaved={resources.replace} onDone={resources.retry} />)}
      </fieldset>
    </div>
  </div>;
}

function LinkedPage() {
  const params = useSearchParams();
  const parseId = (name: string) => { const value = Number(params.get(name)); return Number.isSafeInteger(value) && value > 0 ? value : undefined; };
  const initialQuery: ResourceQuery = { course_id: parseId("course_id") };
  return <NotesPageContent key={params.toString()} initialQuery={initialQuery} />;
}
export default function NotesPage() { return <Suspense fallback={<p role="status">Loading study workspace...</p>}><LinkedPage /></Suspense>; }
