"use client";
import { useEffect, useId, useRef, useState } from "react";
import usePreferences from "@/hooks/usePreferences";
import { formatDateTime } from "@/utils/formatDate";
import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";
import NoteEditor from "./NoteEditor";
import { Note } from "@/types/note";

function NotePreview({ content }: { content: string }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [hasOverflow, setHasOverflow] = useState(false);
  const bodyRef = useRef<HTMLParagraphElement>(null);
  const bodyId = useId();

  useEffect(() => {
    const body = bodyRef.current;
    // Keep the collapse control available while the body is unconstrained.
    if (!body || isExpanded) return;
    let active = true;
    const measure = () => {
      if (active) setHasOverflow(body.scrollHeight > body.clientHeight);
    };
    const frame = requestAnimationFrame(measure);
    const observer = new ResizeObserver(measure);
    observer.observe(body);
    void document.fonts.ready.then(measure);
    return () => {
      active = false;
      cancelAnimationFrame(frame);
      observer.disconnect();
    };
  }, [isExpanded]);

  const toggle = () => setIsExpanded((expanded) => !expanded);

  return <>
    <p
      id={bodyId}
      ref={bodyRef}
      className={`note-body whitespace-pre-line break-words${isExpanded ? "" : " line-clamp-6"}`}
    >{content}</p>
    {hasOverflow && <button type="button" className="note-preview-toggle" aria-expanded={isExpanded} aria-controls={bodyId} onClick={toggle}>
      {isExpanded ? "Show less" : "Read more"}
    </button>}
  </>;
}

export default function NoteCard({ note, onDelete, onSaved, onDone }: {
  note: Note; onDelete: (id: number) => void; onSaved: (note: Note) => void; onDone: () => void;
}) {
  const { settings } = usePreferences();
  const [editing, setEditing] = useState(false);
  if (editing) return <NoteEditor note={note} onSaved={onSaved} onDone={() => { setEditing(false); onDone(); }} />;
  return <Card className="note-card"><article className="note-reading"><div className="note-card-meta"><span>{note.subject}</span><time dateTime={note.updatedAt}>Updated {formatDateTime(note.updatedAt, settings)}</time></div><h2 className="text-2xl font-semibold mb-5 break-words">{note.title}</h2><NotePreview key={note.content} content={note.content} /></article><div className="note-card-actions"><Button className="w-auto" variant="secondary" onClick={() => setEditing(true)}>Edit note</Button><Button className="w-auto" variant="danger" onClick={() => onDelete(note.id)}>Delete note</Button></div></Card>;
}
