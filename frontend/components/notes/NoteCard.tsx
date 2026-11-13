"use client";
import { useState } from "react";
import usePreferences from "@/hooks/usePreferences";
import { formatDateTime } from "@/utils/formatDate";
import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";
import NoteEditor from "./NoteEditor";
import { Note } from "@/types/note";

export default function NoteCard({ note, onDelete, onSaved, onDone }: {
  note: Note; onDelete: (id: number) => void; onSaved: (note: Note) => void; onDone: () => void;
}) {
  const { settings } = usePreferences();
  const [editing, setEditing] = useState(false);
  if (editing) return <NoteEditor note={note} onSaved={onSaved} onDone={() => { setEditing(false); onDone(); }} />;
  return <Card className="note-card"><article className="note-reading"><div className="note-card-meta"><span>{note.subject}</span><time dateTime={note.updatedAt}>Updated {formatDateTime(note.updatedAt, settings)}</time></div><h2 className="text-2xl font-semibold mb-5 break-words">{note.title}</h2><p className="whitespace-pre-wrap break-words">{note.content}</p></article><div className="note-card-actions"><Button className="w-auto" variant="secondary" onClick={() => setEditing(true)}>Edit note</Button><Button className="w-auto" variant="danger" onClick={() => onDelete(note.id)}>Delete note</Button></div></Card>;
}
