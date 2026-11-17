"use client";

import { apiRequest } from "@/lib/api/client";
import Link from "next/link";
import { useEffect, useId, useRef, useState } from "react";
import { courseApi, goalApi, ResourcePage, ResourceQuery } from "@/lib/api/resources";

type Choice = { id: number; title: string };
type Props = {
  value: number | null | undefined; onChange: (id: number | null, title: string) => void;
  emptyLabel?: string; placeholder?: string; onReset?: () => void; completedFocusOnly?: boolean; label?: string; selectedLabel?: string; required?: boolean; disabled?: boolean;
};

function Picker({ value, onChange, label, emptyLabel, placeholder: inputPlaceholder, onReset, completedFocusOnly, selectedLabel, required, disabled, kind, courseId }: Props & {
  label: string; kind: "courses" | "goals"; courseId?: number;
}) {
  const id = useId();
  const input = useRef<HTMLInputElement>(null);
  const list = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [result, setResult] = useState<ResourcePage<Choice> | null>(null);
  const [selected, setSelected] = useState<Choice | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [revision, setRevision] = useState(0);
  const [active, setActive] = useState(0);
  const emptyChoiceLabel = emptyLabel ?? (required ? `Choose a ${kind === "courses" ? "course" : "goal"}` : kind === "goals" ? "No linked goal" : "All courses");
  const placeholder = inputPlaceholder ?? emptyChoiceLabel;
  const items: (Choice | null | undefined)[] = [
    ...(onReset ? [undefined] : []),
    ...(required || onReset ? [] : [null]),
    ...(result?.items ?? []),
    ...(onReset && !required ? [null] : []),
  ];
  const choiceId = (choice: Choice | null | undefined) => choice === undefined ? undefined : choice?.id ?? null;
  const title = value == null ? selectedLabel ?? "" : selectedLabel || (selected?.id === value ? selected.title : result?.items.find((item) => item.id === value)?.title) || "";
  const hasMore = !!result && page < result.total_pages && page * 100 <= 10000;

  useEffect(() => {
    input.current?.setCustomValidity(required && value == null ? `Choose a ${kind === "courses" ? "course" : "goal"} from the list.` : "");
  }, [required, value, kind]);

  useEffect(() => {
    if (value == null || selectedLabel) return;
    const controller = new AbortController();
    void apiRequest<Choice>(`/api/v1/${kind}/${value}`, { signal: controller.signal })
      .then((choice) => { if (!controller.signal.aborted) setSelected(choice); })
      .catch((failure) => { if (!controller.signal.aborted) setError(failure instanceof Error ? failure.message : "Unable to load selection."); });
    return () => controller.abort();
  }, [kind, value, selectedLabel]);

  useEffect(() => {
    if (!open || disabled) return;
    const controller = new AbortController();
    const timeout = setTimeout(async () => {
      try {
        const query: ResourceQuery = { page, limit: 100, sort_by: "title", order: "asc", search: search || undefined, ...(kind === "goals" ? { course_id: courseId } : {}), ...(kind === "courses" && completedFocusOnly ? { has_completed_focus: true } : {}) };
        const data = await (kind === "courses" ? courseApi : goalApi).list(query, controller.signal);
        if (!controller.signal.aborted) {
          setResult((previous) => ({ ...data, items: page === 1 ? data.items : [...(previous?.items ?? []), ...data.items.filter((item) => !previous?.items.some((old) => old.id === item.id))] }));
          setError(null);
        }
      } catch (failure) { if (!controller.signal.aborted) setError(failure instanceof Error ? failure.message : "Unable to load choices."); }
      finally { if (!controller.signal.aborted) setLoading(false); }
    }, 200);
    return () => { clearTimeout(timeout); controller.abort(); };
  }, [kind, courseId, completedFocusOnly, page, search, revision, open, disabled]);

  useEffect(() => {
    list.current?.querySelector(`[data-index="${active}"]`)?.scrollIntoView({ block: "nearest" });
  }, [active]);

  function show() {
    if (open || disabled || input.current?.matches(":disabled")) return;
    setSearch(""); setPage(1); setResult(null); setActive(0); setError(null); setLoading(true); setOpen(true);
  }
  function toggle() {
    if (open) setOpen(false);
    else { input.current?.focus(); show(); }
  }
  function choose(choice: Choice | null | undefined) {
    if (disabled || input.current?.matches(":disabled")) return;
    setSelected(choice ?? null); if (choice === undefined) onReset?.(); else onChange(choice?.id ?? null, choice?.title ?? ""); setOpen(false); setSearch("");
  }
  function more() { if (hasMore && !loading && !error) { setLoading(true); setPage((previous) => previous + 1); } }

  return <div className="study-picker" onBlur={(event) => { if (!event.currentTarget.contains(event.relatedTarget)) setOpen(false); }}>
    <label htmlFor={id} className="text-muted block text-sm font-medium mb-2">{label}{required ? " *" : " (optional)"}</label>
    <div className="study-combobox">
      <input ref={input} id={id} role="combobox" aria-autocomplete="list" aria-expanded={open && !disabled}
        aria-controls={`${id}-options`} aria-activedescendant={open && active >= 0 && active < items.length ? `${id}-option-${active}` : undefined}
        autoComplete="off" maxLength={200} required={required} disabled={disabled} className="input-theme study-combobox-input"
        placeholder={placeholder} value={open ? search : title} onClick={toggle}
        onChange={(event) => { setSearch(event.target.value); setPage(1); setResult(null); setActive(0); setError(null); setLoading(true); setOpen(true); }}
        onKeyDown={(event) => {
          if (event.key === "Escape") { event.preventDefault(); event.stopPropagation(); setOpen(false); }
          else if (event.key === "ArrowDown" || event.key === "ArrowUp") {
            event.preventDefault();
            if (!open) show();
            else { setActive((previous) => Math.max(0, Math.min(items.length - 1, previous + (event.key === "ArrowDown" ? 1 : -1)))); if (event.key === "ArrowDown" && active >= items.length - 1) more(); }
          } else if (event.key === "Enter" && open) { event.preventDefault(); if (active >= 0 && active < items.length) choose(items[active]); }
        }} />
      <button type="button" className="study-combobox-toggle" disabled={disabled} aria-label={`${open ? "Close" : "Open"} ${label.toLowerCase()} options`} aria-expanded={open && !disabled} aria-controls={`${id}-options`}
        onMouseDown={(event) => event.preventDefault()} onClick={toggle}
        onKeyDown={(event) => { if (event.key === "Escape") { event.preventDefault(); setOpen(false); input.current?.focus(); } }}>
        <span aria-hidden="true">⌄</span>
      </button>
      {open && !disabled && <div className="study-combobox-menu">
        <div ref={list} id={`${id}-options`} role="listbox" aria-label={label} aria-busy={loading}
          className="study-combobox-options" onScroll={(event) => { const node = event.currentTarget; if (node.scrollHeight - node.scrollTop - node.clientHeight < 60) more(); }}>
          {items.map((choice, index) => <div key={choice === undefined ? "reset" : choice?.id ?? "empty"} id={`${id}-option-${index}`} role="option"
            aria-selected={choiceId(choice) === value} data-index={index}
            className={`study-combobox-option${index === active ? " is-active" : ""}`}
            onMouseDown={(event) => event.preventDefault()} onMouseEnter={() => setActive(index)} onClick={() => choose(choice)}>
            <span>{choice === undefined ? placeholder : choice?.title ?? emptyChoiceLabel}</span>{choiceId(choice) === value && <span aria-hidden="true">✓</span>}
          </div>)}
          {loading && <p role="status" className="study-combobox-message">Loading {kind}…</p>}
          {!loading && result?.total === 0 && <p className="study-combobox-message">{search ? "No matches. Try another name." : `No ${kind} available yet.`}</p>}
          {result && !hasMore && result.total > result.items.length && <p className="study-combobox-message">Type a name to narrow this list.</p>}
        </div>
        {error && <p role="alert" className="study-combobox-message">{error} <button type="button" onClick={() => { setLoading(true); setRevision((current) => current + 1); }}>Retry</button></p>}
      </div>}
    </div>
    {kind === "courses" && !completedFocusOnly && <Link href="/courses" className="text-action text-xs mt-2">Manage courses</Link>}
  </div>;
}

export function CourseSelect(props: Props) { return <Picker {...props} label={props.label ?? "Course"} kind="courses" />; }
export function GoalSelect(props: Props & { courseId: number }) { return <Picker key={props.courseId} {...props} label={props.label ?? "Contribute to goal"} kind="goals" />; }
