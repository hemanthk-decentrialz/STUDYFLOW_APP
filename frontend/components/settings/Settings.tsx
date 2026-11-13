"use client";

import { FormEvent, useEffect, useState } from "react";

import Link from "next/link";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faDownload } from "@fortawesome/free-solid-svg-icons";

import { confirmAction, notify } from "@/components/ui/DataSyncStatus";

import Card from "@/components/ui/Card";

import Button from "@/components/ui/Button";

import { useAuth } from "@/context/AuthContext";

import usePreferences from "@/hooks/usePreferences";

import { exportStudyData, getDeletedResources, resetStudyData } from "@/lib/api/settings";

import { restoreResource, ResourcePage } from "@/lib/api/resources";

import { refreshTimerState, resetWorkspace, retryPendingState } from "@/lib/api/state";

import { DeletedResource, StudyFlowSettings } from "@/types/settings";

import { formatDateTime } from "@/utils/formatDate";

const resourceLabels = { courses: "Course", notes: "Note", goals: "Goal", "study-sessions": "Planner session" };

function PreferencesForm({ settings, saving, onSave }: { settings: StudyFlowSettings; saving: boolean; onSave: (settings: StudyFlowSettings) => Promise<void> }) {

  const [draft, setDraft] = useState(settings);

  const [permission, setPermission] = useState<string | null>(null);

  const change = <Key extends keyof StudyFlowSettings>(key: Key, value: StudyFlowSettings[Key]) => setDraft((previous) => ({ ...previous, [key]: value }));

  const zones = Array.from(new Set([draft.timeZone, Intl.DateTimeFormat().resolvedOptions().timeZone, ...Intl.supportedValuesOf("timeZone")])).sort();

  async function requestNotifications() {

    if (!("Notification" in window)) { setPermission("Browser notifications unavailable. In-app reminders still work."); return; }

    const result = await Notification.requestPermission();

    setPermission(result === "granted" ? "Notifications enabled on this device." : "Notifications blocked. Enable them in browser settings.");

  }

  function submit(event: FormEvent) { event.preventDefault(); void onSave(draft); }

  return <form onSubmit={submit}>

    <fieldset disabled={saving} className="space-y-6">

      <Card><section className="settings-section" aria-labelledby="appearance-heading"><h2 id="appearance-heading">Appearance</h2><p>Choose the workspace theme.</p><div className="settings-fields"><label>Theme<select className="input-theme" value={draft.theme} onChange={(event) => change("theme", event.target.value as StudyFlowSettings["theme"])}><option value="light">Light</option><option value="dark">Dark</option></select></label></div></section></Card>

      <Card><section id="focus-preferences" className="settings-section" aria-labelledby="focus-heading"><h2 id="focus-heading">Focus preferences</h2><p>Set durations for new focus sessions and breaks.</p><div className="settings-fields">

        <label>Focus duration (minutes)<input className="input-theme" type="number" required min={1} max={120} value={draft.focusMinutes} onChange={(event) => change("focusMinutes", Number(event.target.value))} /></label>

        <label>Short break (minutes)<input className="input-theme" type="number" required min={1} max={30} value={draft.shortBreakMinutes} onChange={(event) => change("shortBreakMinutes", Number(event.target.value))} /></label>

        <label>Long break (minutes)<input className="input-theme" type="number" required min={1} max={60} value={draft.longBreakMinutes} onChange={(event) => change("longBreakMinutes", Number(event.target.value))} /></label>

        <label className="settings-check"><input type="checkbox" checked={draft.completionSound} onChange={(event) => change("completionSound", event.target.checked)} />Play a sound when a timer finishes</label>

      </div></section></Card>

      <Card><section className="settings-section" aria-labelledby="calendar-heading"><h2 id="calendar-heading">Calendar preferences</h2><p>Choose your week start, time zone and clock format.</p><div className="settings-fields">

        <label>Week starts on<select className="input-theme" value={draft.weekStartsOn} onChange={(event) => change("weekStartsOn", event.target.value as StudyFlowSettings["weekStartsOn"])}><option value="monday">Monday</option><option value="sunday">Sunday</option></select></label>

        <label>Time zone<select className="input-theme" value={draft.timeZone} onChange={(event) => change("timeZone", event.target.value)}>{zones.map((zone) => <option key={zone} value={zone}>{zone.replaceAll("_", " ")}</option>)}</select></label>

        <label>Time format<select className="input-theme" value={draft.timeFormat} onChange={(event) => change("timeFormat", event.target.value as StudyFlowSettings["timeFormat"])}><option value="24h">24-hour</option><option value="12h">12-hour</option></select></label>

      </div></section></Card>

      <Card><section className="settings-section" aria-labelledby="reminders-heading"><h2 id="reminders-heading">Reminders</h2><p>Get reminders while Studyflow is open.</p><div className="settings-fields">

        <label className="settings-check"><input type="checkbox" checked={draft.sessionReminders} onChange={(event) => change("sessionReminders", event.target.checked)} />Upcoming study sessions</label>

        <label className="settings-check"><input type="checkbox" checked={draft.deadlineReminders} onChange={(event) => change("deadlineReminders", event.target.checked)} />Goal deadlines (9 AM)</label>

        <label>Remind me before (minutes)<input className="input-theme" type="number" required min={5} max={120} value={draft.reminderLeadMinutes} onChange={(event) => change("reminderLeadMinutes", Number(event.target.value))} /></label>

        <div className="self-end"><Button type="button" variant="secondary" className="settings-action" onClick={() => { void requestNotifications().catch(() => setPermission("Could not enable notifications. Check browser settings.")); }}>Allow browser notifications</Button></div>

      </div>{permission && <p role="status" className="text-muted text-sm mt-4">{permission}</p>}</section></Card>

      <div className="settings-row"><p className="text-muted text-sm">Save to apply your changes.</p><Button type="submit" className="settings-action" loading={saving}>Save preferences</Button></div>

    </fieldset>

  </form>;

}

function RecentlyDeleted({ settings }: { settings: StudyFlowSettings }) {

  const [page, setPage] = useState(1);

  const [kind, setKind] = useState("");

  const [result, setResult] = useState<ResourcePage<DeletedResource> | null>(null);

  const [loading, setLoading] = useState(true);

  const [pending, setPending] = useState<string | null>(null);

  const [error, setError] = useState("");

  const [revision, setRevision] = useState(0);

  useEffect(() => {

    const controller = new AbortController();

    async function load() {

      setLoading(true);

      try {

        const data = await getDeletedResources(page, kind, controller.signal);

        if (!controller.signal.aborted) {

          if (page > Math.max(1, data.total_pages)) { setPage(Math.max(1, data.total_pages)); return; }

          setResult(data); setError("");

        }

      } catch (failure) { if (!controller.signal.aborted) setError(failure instanceof Error ? failure.message : "Unable to load deleted items."); }

      finally { if (!controller.signal.aborted) setLoading(false); }

    }

    void load();

    const refresh = () => setRevision((value) => value + 1);

    window.addEventListener("studyflow-resource-restored", refresh);

    window.addEventListener("focus", refresh);

    return () => { controller.abort(); window.removeEventListener("studyflow-resource-restored", refresh); window.removeEventListener("focus", refresh); };

  }, [page, kind, revision]);

  async function restore(item: DeletedResource) {

    setPending(`${item.kind}:${item.id}`); setError("");

    try {

      await restoreResource(item.kind === "study-sessions" ? "planner" : item.kind, item.id);

      window.dispatchEvent(new Event("studyflow-resource-restored"));

      window.dispatchEvent(new Event("studyflow-data-saved"));

      notify(`${resourceLabels[item.kind]} restored.`);

    } catch (failure) { setError(failure instanceof Error ? failure.message : "Unable to restore this item."); }

    finally { setPending(null); }

  }

  return <Card><section className="settings-section" aria-labelledby="trash-heading"><h2 id="trash-heading">Recently deleted</h2><p>Restore deleted items. Restore their course first.</p>

    <div className="settings-fields"><label>Item type<select className="input-theme" value={kind} disabled={!!pending} onChange={(event) => { setKind(event.target.value); setPage(1); }}><option value="">All items</option>{Object.entries(resourceLabels).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label></div>

    {error && <p role="alert" className="feedback-error">{error} <button type="button" onClick={() => setRevision((value) => value + 1)}>Retry</button></p>}

    {loading && <p role="status" className="text-muted text-sm mt-4">Loading deleted items…</p>}

    {!loading && result?.total === 0 && <p className="text-muted mt-5">No deleted items.</p>}

    <ul className="settings-trash-list">{result?.items.map((item) => <li key={`${item.kind}:${item.id}`}><div><strong>{item.title}</strong><p>{resourceLabels[item.kind]} · Deleted {formatDateTime(item.deletedAt, settings)}</p></div><Button type="button" variant="secondary" className="settings-action" disabled={loading || !!pending} loading={pending === `${item.kind}:${item.id}`} onClick={() => { void restore(item); }}>Restore</Button></li>)}</ul>

    {result && result.total_pages > 1 && <div className="resource-pagination mt-4"><button type="button" disabled={loading || !!pending || page <= 1} onClick={() => setPage((value) => value - 1)}>Previous</button><span className="text-sm">{page} / {result.total_pages}</span><button type="button" disabled={loading || !!pending || page >= result.total_pages || page * 10 > 10000} onClick={() => setPage((value) => value + 1)}>Next</button></div>}

  </section></Card>;

}

export default function Settings() {

  const { user } = useAuth();

  const { settings, setSettings, ready } = usePreferences();

  const [saving, setSaving] = useState(false);

  const [exporting, setExporting] = useState(false);

  const [resetting, setResetting] = useState(false);

  async function save(next: StudyFlowSettings) {

    setSaving(true);

    try { setSettings(next); await retryPendingState(); await refreshTimerState(); notify("Preferences saved."); }

    catch (failure) { notify(failure instanceof Error ? failure.message : "Unable to save preferences. Try saving again.", { error: true }); }

    finally { setSaving(false); }

  }

  async function download() {

    setExporting(true);

    try {

      const data = await exportStudyData();

      const url = URL.createObjectURL(data);

      const link = document.createElement("a"); link.href = url; link.download = `studyflow-export-${new Date().toISOString().slice(0, 10)}.json`;

      document.body.append(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 30000);

      notify("Your study data download is ready.");

    } catch (failure) { notify(failure instanceof Error ? failure.message : "Unable to export your data.", { error: true }); }

    finally { setExporting(false); }

  }

  async function resetApplication() {

    if (!await confirmAction("Permanently remove courses, planner sessions, notes, goals and focus history, including Recently deleted? This cannot be undone. Your account and preferences are kept.")) return;

    setResetting(true);

    try {

      await resetWorkspace(resetStudyData);

      try { if (user) Object.keys(localStorage).filter((key) => key.startsWith(`user:${user.id}:`)).forEach((key) => localStorage.removeItem(key)); } catch { /* Server reset has completed even if device storage is unavailable. */ }

      location.reload();

    } catch (failure) { notify(failure instanceof Error ? failure.message : "Unable to reset your data.", { error: true }); setResetting(false); }

  }

  if (!ready) return <p role="status">Loading preferences…</p>;

  return <div className="settings-page space-y-6">

    <PreferencesForm key={JSON.stringify(settings)} settings={settings} saving={saving || resetting} onSave={save} />

    <Card><section className="settings-section settings-row" aria-labelledby="export-heading"><div><h2 id="export-heading">Data export</h2><p className="text-muted text-sm mt-2">Download your study data as JSON.</p></div><Button type="button" variant="secondary" className="settings-action settings-download" aria-label="Download study data as JSON" title="Download study data" loading={exporting} disabled={resetting || saving} onClick={() => { void download(); }}>{!exporting && <FontAwesomeIcon icon={faDownload} aria-hidden="true" />}</Button></section></Card>

    <RecentlyDeleted settings={settings} />

    <Card><section className="settings-section settings-row" aria-labelledby="reset-heading"><div><h2 id="reset-heading">Reset application</h2><p className="text-muted text-sm mt-2">Permanently delete study data; keep your account and preferences.</p><Link className="text-sm text-(--primary) inline-block mt-2" href="/profile">Manage your profile</Link></div><Button type="button" variant="danger" className="settings-action" loading={resetting} disabled={saving || exporting} onClick={() => { void resetApplication(); }}>Reset data</Button></section></Card>

  </div>;

}
