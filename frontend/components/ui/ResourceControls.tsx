"use client";

import { CourseSelect } from "./StudyLinks";
import { ReactNode, useId, useRef, useState } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faArrowLeft, faArrowRight, faChevronDown, faMagnifyingGlass, faRotateLeft, faSliders, faXmark } from "@fortawesome/free-solid-svg-icons";
import { ResourceModule, ResourcePage, ResourceQuery } from "@/lib/api/resources";

interface Props {
  title: string; description?: string;
  module: ResourceModule; query: ResourceQuery; data?: ResourcePage<unknown>;
  loading: boolean; error: string | null; retry: () => void;
  onChange: (query: ResourceQuery) => void;
}

const sortLabels: Record<string, string> = {
  position: "Added order", id: "Added order", title: "Title", subject: "Course name",
  scheduled_date: "Study date", time: "Study time", priority: "Priority", completed: "Completion",
  duration_minutes: "Duration", created_at: "Date created", updated_at: "Last updated",
  deadline: "Deadline", progress: "Progress",
};

function Field({ id, label, children, wide = false }: {
  id: string; label: string; children: ReactNode; wide?: boolean;
}) {
  return <div className={`resource-filter-field${wide ? " resource-filter-wide" : ""}`}>
    <label htmlFor={id}>{label}</label>{children}
  </div>;
}

export default function ResourceControls({ title, description, module, query, data, loading, error, retry, onChange }: Props) {
  const [open, setOpen] = useState(false);
  const panelId = useId();
  const trigger = useRef<HTMLButtonElement>(null);
  const id = (field: string) => `${panelId}-${field}`;
  const change = (fields: Partial<ResourceQuery>) => onChange({ ...query, ...fields, page: 1 });
  const activeFields = Object.entries(query).filter(([key, value]) =>
    !["page", "limit", "sort_by", "order"].includes(key) && value !== undefined && value !== "");
  const activeCount = activeFields.length + ((query.sort_by ?? "position") !== "position" || (query.order ?? "asc") !== "asc" ? 1 : 0);
  const sortFields = module === "courses" ? ["position", "title", "created_at", "updated_at"] : module === "planner"
    ? ["position", "scheduled_date", "subject", "time", "priority", "completed", "duration_minutes", "created_at", "updated_at"]
    : ["position", "title", "subject", ...(module === "goals" ? ["deadline", "progress"] : []), "created_at", "updated_at"];
  const orderLabels = ["title", "subject"].includes(query.sort_by ?? "") ? ["A to Z", "Z to A"]
    : ["scheduled_date", "time", "deadline", "created_at", "updated_at"].includes(query.sort_by ?? "") ? ["Earliest first", "Latest first"]
      : query.sort_by === "completed" ? ["Pending first", "Completed first"]
        : query.sort_by === "position" || !query.sort_by ? ["Oldest first", "Newest first"] : ["Lowest first", "Highest first"];
  const offsetCap = (query.page ?? 1) * (query.limit ?? 10) > 10000;
  const close = () => { setOpen(false); trigger.current?.focus(); };
  const reset = () => onChange({ page: 1, limit: query.limit ?? 10, sort_by: "position", order: "asc" });

  return (
    <section aria-label={`${title} controls`} className="resource-controls">
      <div className="resource-page-heading">
        <div className="min-w-0">
          <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">{title}</h1>
          {description && <p className="text-muted mt-2 text-sm leading-6">{description}</p>}
        </div>
        <button ref={trigger} type="button" className="resource-filter-trigger" aria-expanded={open}
          aria-controls={panelId} onClick={() => setOpen((previous) => !previous)}>
          <FontAwesomeIcon icon={faSliders} aria-hidden="true" />
          <span>Filters</span>
          {activeCount > 0 && <span className="resource-filter-count" aria-label={`${activeCount} active`}>{activeCount}</span>}
          <FontAwesomeIcon icon={faChevronDown} className={`resource-filter-chevron${open ? " is-open" : ""}`} aria-hidden="true" />
        </button>
      </div>

      <div id={panelId} hidden={!open} className="resource-filter-panel" role="region" aria-labelledby={id("heading")}
        onKeyDown={(event) => { if (event.key === "Escape") { event.preventDefault(); event.stopPropagation(); close(); } }}>
        <div className="resource-filter-panel-heading">
          <div className="flex min-w-0 items-center gap-3">
            <span className="resource-filter-icon"><FontAwesomeIcon icon={faSliders} aria-hidden="true" /></span>
            <div><h2 id={id("heading")} className="text-sm font-semibold">Filters &amp; sorting</h2>
              <p className="text-muted mt-1 text-xs">Refine your view. Changes apply automatically.</p></div>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <button type="button" className="resource-filter-reset" disabled={activeCount === 0} onClick={reset}>
              <FontAwesomeIcon icon={faRotateLeft} aria-hidden="true" /><span>Reset filters</span>
            </button>
            <button type="button" className="resource-filter-close" aria-label="Close filters" onClick={close}>
              <FontAwesomeIcon icon={faXmark} aria-hidden="true" />
            </button>
          </div>
        </div>
        <div className="resource-filter-grid">
          <Field id={id("search")} label="Search" wide>
            <div className="resource-filter-search">
              <FontAwesomeIcon icon={faMagnifyingGlass} aria-hidden="true" />
              <input id={id("search")} type="search" className="resource-filter-input" value={query.search ?? ""}
                placeholder={module === "notes" ? "Search titles and content…" : module === "goals" ? "Search your goals…" : "Search study subjects…"}
                onChange={(event) => change({ search: event.target.value || undefined })} />
            </div>
          </Field>
          <Field id={id("sort")} label="Sort by">
            <select id={id("sort")} className="resource-filter-input" value={query.sort_by ?? "position"}
              onChange={(event) => change({ sort_by: event.target.value })}>
              {sortFields.map((field) => <option key={field} value={field}>{sortLabels[field]}</option>)}
            </select>
          </Field>
          <Field id={id("order")} label="Order">
            <select id={id("order")} className="resource-filter-input" value={query.order ?? "asc"}
              onChange={(event) => change({ order: event.target.value as "asc" | "desc" })}>
              <option value="asc">{orderLabels[0]}</option><option value="desc">{orderLabels[1]}</option>
            </select>
          </Field>
          {(module === "planner" || module === "goals") && <Field id={id("status")} label="Status">
            <select id={id("status")} className="resource-filter-input" value={query.completed === undefined ? "all" : String(query.completed)}
              onChange={(event) => change({ completed: event.target.value === "all" ? undefined : event.target.value === "true" })}>
              <option value="all">All</option><option value="true">Completed</option><option value="false">Pending</option>
            </select>
          </Field>}
          {module !== "courses" && <div><CourseSelect label="Course filter" value={query.course_id ?? null} onChange={(id) => change({ course_id: id ?? undefined, goal_id: undefined })} /></div>}
          {query.goal_id && <div className="text-sm text-muted">Showing work for the linked goal. <button type="button" className="text-(--primary)" onClick={() => change({ goal_id: undefined })}>Show all goals/sessions</button></div>}
          {module === "planner" && <Field id={id("priority")} label="Priority">
            <select id={id("priority")} className="resource-filter-input" value={query.priority ?? ""}
              onChange={(event) => change({ priority: event.target.value || undefined })}>
              <option value="">All priorities</option>{["High", "Medium", "Low"].map((value) => <option key={value}>{value}</option>)}
            </select>
          </Field>}
          {module === "planner" && <>
            <Field id={id("date-from")} label="Study date from"><input id={id("date-from")} type="date" className="resource-filter-input" value={query.date_from ?? ""} onChange={(event) => change({ date_from: event.target.value || undefined })} /></Field>
            <Field id={id("date-to")} label="Study date to"><input id={id("date-to")} type="date" className="resource-filter-input" value={query.date_to ?? ""} onChange={(event) => change({ date_to: event.target.value || undefined })} /></Field>
          </>}
          {module === "goals" && <>
            <Field id={id("deadline-from")} label="Deadline from">
              <input id={id("deadline-from")} type="date" className="resource-filter-input" value={query.deadline_from ?? ""}
                onChange={(event) => change({ deadline_from: event.target.value || undefined })} />
            </Field>
            <Field id={id("deadline-to")} label="Deadline to">
              <input id={id("deadline-to")} type="date" className="resource-filter-input" value={query.deadline_to ?? ""}
                onChange={(event) => change({ deadline_to: event.target.value || undefined })} />
            </Field>
            <Field id={id("progress-min")} label="Minimum progress (%)">
              <input id={id("progress-min")} type="number" min={0} max={100} className="resource-filter-input" value={query.progress_min ?? ""}
                placeholder="0" onChange={(event) => change({ progress_min: event.target.value === "" ? undefined : Number(event.target.value) })} />
            </Field>
            <Field id={id("progress-max")} label="Maximum progress (%)">
              <input id={id("progress-max")} type="number" min={0} max={100} className="resource-filter-input" value={query.progress_max ?? ""}
                placeholder="100" onChange={(event) => change({ progress_max: event.target.value === "" ? undefined : Number(event.target.value) })} />
            </Field>
          </>}
          <Field id={id("limit")} label="Results per page">
            <select id={id("limit")} className="resource-filter-input" value={query.limit ?? 10}
              onChange={(event) => change({ limit: Number(event.target.value) })}>
              {[10, 20, 50, 100].map((limit) => <option key={limit}>{limit}</option>)}
            </select>
          </Field>
        </div>
      </div>

      {error && <div className="resource-results-error" role="alert"><p>{error}</p>
        <button type="button" onClick={retry}>Retry</button></div>}
      <div className="resource-results-toolbar">
        <p className="text-muted text-xs" role="status" aria-live="polite">
          {loading ? "Loading results…" : data ? <><strong>{data.total}</strong> {data.total === 1 ? "result" : "results"}{data.total_pages > 1 && <><span className="resource-results-separator" aria-hidden="true">·</span>Page {query.page ?? 1} of {data.total_pages}</>}</> : "Results unavailable"}
        </p>
        {data && data.total_pages > 1 && <div className="resource-pagination" aria-label="Pagination">
          <button type="button" disabled={loading || (query.page ?? 1) <= 1}
            onClick={() => onChange({ ...query, page: (query.page ?? 1) - 1 })}>
            <FontAwesomeIcon icon={faArrowLeft} aria-hidden="true" /><span>Previous</span>
          </button>
          <button type="button" disabled={loading || offsetCap || (query.page ?? 1) >= (data?.total_pages ?? 0)}
            onClick={() => onChange({ ...query, page: (query.page ?? 1) + 1 })}>
            <span>Next</span><FontAwesomeIcon icon={faArrowRight} aria-hidden="true" />
          </button>
        </div>}
      </div>
      {offsetCap && (query.page ?? 1) < (data?.total_pages ?? 0) && <p className="text-muted mt-2 text-xs">Narrow your filters to see more results.</p>}
    </section>
  );
}
