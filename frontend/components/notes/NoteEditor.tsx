"use client";

import { useEffect, useRef, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { ApiRequestError } from "@/lib/api/client";
import { noteApi } from "@/lib/api/resources";
import { Note, NoteInput } from "@/types/note";
import { CourseSelect } from "@/components/ui/StudyLinks";
import Button from "@/components/ui/Button";
import Card from "@/components/ui/Card";

type Draft = { id: number; title: string; content: string; courseId: number | null; baseVersion: number };
export default function NoteEditor({ note, onAddNote, onSaved, onDone, initialCourseId }: {
  note?: Note; onAddNote?: (note: NoteInput) => Promise<Note>; onSaved?: (note: Note) => void;
  onDone?: () => void; initialCourseId?: number;
}) {
  const { user } = useAuth();
  const cacheKey = `user:${user?.id}:note-draft:${note?.id ?? `new:${initialCourseId ?? "all"}`}`;
  const [initial] = useState(() => {
    const base: Draft = { id: note?.id ?? Date.now(), title: note?.title ?? "", content: note?.content ?? "", courseId: note?.courseId ?? initialCourseId ?? null, baseVersion: note?.version ?? 1 };
    try {
      const cached = JSON.parse(localStorage.getItem(cacheKey) ?? "null") as Draft | null;
      if (cached && Number.isSafeInteger(cached.id) && cached.id > 0 && typeof cached.title === "string" && typeof cached.content === "string" && cached.title.length <= 200 && cached.content.length <= 100000 && (cached.courseId === null || (Number.isSafeInteger(cached.courseId) && cached.courseId > 0)) && Number.isInteger(cached.baseVersion) && cached.baseVersion >= 1 && (!note || cached.id === note.id)) return { base, draft: cached, recovered: true };
    } catch { /* An unavailable or invalid device draft does not block server notes. */ }
    return { base, draft: base, recovered: false };
  });
  const [draft, setDraft] = useState(initial.draft);
  const [recovery, setRecovery] = useState(initial.recovered);
  const [conflict, setConflict] = useState<Note | null>(note && initial.draft.baseVersion !== note.version ? note : null);
  const [error, setError] = useState("");
  const [status, setStatus] = useState(initial.recovered ? "Recovered draft, not saved" : note ? "Saved" : "Draft on this device");
  const [busy, setBusy] = useState(false);
  const [cycle, setCycle] = useState(0);
  const latest = useRef(draft), saved = useRef(initial.base), version = useRef(initial.draft.baseVersion), saving = useRef(false), active = useRef(true);
  const dirty = (value: Draft) => value.title !== saved.current.title || value.content !== saved.current.content || value.courseId !== saved.current.courseId;
  const valid = (value: Draft) => !!value.courseId && !!value.title.trim() && !!value.content.trim();
  const writeDraft = () => { try { if (dirty(latest.current) || (!note && !!(latest.current.title || latest.current.content))) localStorage.setItem(cacheKey, JSON.stringify({ ...latest.current, baseVersion: version.current })); else localStorage.removeItem(cacheKey); } catch { setError("Device draft recovery is unavailable. Save before leaving this page."); } };
  useEffect(() => { latest.current = draft; }, [draft]);
  useEffect(() => {
    active.current = true;
    const flush = () => { try { if (dirty(latest.current) || (!note && !!(latest.current.title || latest.current.content))) localStorage.setItem(cacheKey, JSON.stringify({ ...latest.current, baseVersion: version.current })); } catch { /* The editor reports device storage failures while open. */ } };
    window.addEventListener("pagehide", flush);
    return () => { active.current = false; flush(); window.removeEventListener("pagehide", flush); };
  }, [cacheKey, note]);

  async function save(overwrite?: Note) {
    if (saving.current || (recovery && !overwrite) || (conflict && !overwrite)) return;
    if (!valid(latest.current)) { setError(!latest.current.courseId ? "Choose a course." : !latest.current.title.trim() ? "Enter a note title." : "Enter some note content."); setStatus("Not saved"); return; }
    const snapshot = { ...latest.current };
    if (note && !dirty(snapshot) && !overwrite) return;
    saving.current = true; setBusy(true); setError(""); setStatus("Saving…");
    try {
      const payload: NoteInput = { id: snapshot.id, courseId: snapshot.courseId!, subject: "", title: snapshot.title, content: snapshot.content };
      let result: Note;
      if (note) result = await noteApi.patch(note.id, { expectedVersion: overwrite?.version ?? version.current, title: snapshot.title, content: snapshot.content, courseId: snapshot.courseId! });
      else {
        try { result = onAddNote ? await onAddNote(payload) : await noteApi.create(payload); }
        catch (failure) {
          if (!(failure instanceof ApiRequestError) || failure.status !== 409) throw failure;
          const existing = await noteApi.get(snapshot.id).catch(() => null);
          if (!existing || existing.title !== snapshot.title.trim() || existing.content !== snapshot.content || existing.courseId !== snapshot.courseId) throw failure;
          result = existing;
        }
      }
      if (!active.current) return;
      version.current = result.version; saved.current = { ...snapshot, title: result.title, baseVersion: result.version };
      if (latest.current.title === snapshot.title && latest.current.title !== result.title) { latest.current = { ...latest.current, title: result.title }; setDraft(latest.current); }
      setConflict(null); setRecovery(false); setStatus(dirty(latest.current) ? "Unsaved changes" : "Saved"); onSaved?.(result);
      if (!note) { const blank = { ...initial.base, id: Date.now(), title: "", content: "", courseId: snapshot.courseId }; latest.current = blank; saved.current = blank; setDraft(blank); localStorage.removeItem(cacheKey); setStatus("Note created"); }
      else if (!dirty(latest.current)) localStorage.removeItem(cacheKey);
      window.dispatchEvent(new Event("studyflow-data-saved"));
    } catch (failure) {
      if (!active.current) return;
      setStatus("Not saved"); setError(failure instanceof Error ? failure.message : "Unable to save this note.");
      if (note && failure instanceof ApiRequestError && failure.status === 409) {
        const remote = await noteApi.get(note.id).catch(() => null);
        if (active.current && remote && remote.version !== version.current) setConflict(remote);
      }
    } finally { saving.current = false; if (active.current) { setBusy(false); setCycle((value) => value + 1); } }
  }
  useEffect(() => {
    const timeout = setTimeout(() => { writeDraft(); if (note && !recovery && !conflict && !error && valid(latest.current) && dirty(latest.current)) void save(); }, 900);
    return () => clearTimeout(timeout);
  // Save reads the latest refs; incoming server props never replace an unsaved draft.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [draft, recovery, conflict, cycle]);
  const change = (changes: Partial<Draft>) => { const next = { ...latest.current, ...changes }; latest.current = next; setDraft(next); setError(""); setStatus(note ? "Unsaved changes" : "Draft on this device"); };
  return <Card className={`note-editor${note ? "" : " form-panel"}`}><h2 className="text-xl font-semibold mb-4">{note ? "Edit note" : "Create note"}</h2>
    <p id={`note-status-${draft.id}`} role="status" aria-live="polite" className="text-muted text-xs mb-4">{status}{note ? " · Autosaves after you stop typing" : " · Create to save to your account"}</p>
    {recovery && <div className="feedback-error"><p>A device draft was recovered. Review it before saving.</p><button type="button" onClick={() => { setRecovery(false); setStatus("Unsaved changes"); }}>Resume draft</button><button type="button" onClick={() => { latest.current = initial.base; saved.current = initial.base; version.current = initial.base.baseVersion; setDraft(initial.base); setRecovery(false); setConflict(null); setError(""); setStatus(note ? "Saved" : "Draft on this device"); localStorage.removeItem(cacheKey); }}>Discard recovered draft</button></div>}
    {error && <p role="alert" className="feedback-error">{error}</p>}
    {conflict && <section className="feedback-error" aria-label="Note version conflict"><h3 className="font-semibold">This note changed elsewhere</h3><p>Your draft is kept below. Review the server version before choosing.</p><details><summary>Latest server version</summary><h4>{conflict.title}</h4><p className="whitespace-pre-wrap">{conflict.content}</p></details><div className="flex flex-wrap gap-4 mt-3"><button disabled={busy} onClick={() => { const base = { id: conflict.id, title: conflict.title, content: conflict.content, courseId: conflict.courseId, baseVersion: conflict.version }; saved.current = base; latest.current = base; version.current = conflict.version; setDraft(base); onSaved?.(conflict); setConflict(null); setRecovery(false); setError(""); setStatus("Saved"); localStorage.removeItem(cacheKey); }}>Use server version</button><button disabled={busy} onClick={() => void save(conflict)}>Save my version instead</button></div></section>}
    <form onSubmit={(event) => { event.preventDefault(); void save(); }}><fieldset disabled={busy && !note} className="space-y-4">
      <label className="block text-sm">Title<input required maxLength={200} className="input-theme w-full rounded-lg p-3 mt-2" value={draft.title} onChange={(event) => change({ title: event.target.value })} /></label>
      <CourseSelect required value={draft.courseId} selectedLabel={draft.courseId === note?.courseId ? note.subject : undefined} onChange={(id) => change({ courseId: id })} />
      <label className="block text-sm">Note content<textarea aria-label="Note content" aria-describedby={`note-status-${draft.id}`} required rows={note ? 16 : 8} maxLength={100000} className="input-theme note-writing w-full rounded-lg p-3 mt-2" value={draft.content} onChange={(event) => change({ content: event.target.value })} /></label>
      <div className="note-actions"><Button type="submit" disabled={busy || recovery || !!conflict} loading={busy}>{note ? "Save now" : "Create note"}</Button>{note && <Button type="button" variant="secondary" disabled={busy || !!conflict || recovery} onClick={async () => { if (dirty(latest.current) && !conflict) await save(); if (!dirty(latest.current)) onDone?.(); }}>Done</Button>}{note && <button type="button" disabled={busy} className="text-sm text-muted" onClick={onDone}>Close, keep device draft</button>}</div>
    </fieldset></form>
  </Card>;
}
