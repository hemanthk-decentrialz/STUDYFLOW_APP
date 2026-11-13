"use client";

import { useEffect, useRef, useState } from "react";
import { retryPendingState } from "@/lib/api/state";
import { useAuth } from "@/context/AuthContext";

type Notice = { id: string; message: string; error?: boolean; action?: { label: string; run: () => Promise<unknown> } };
type Confirmation = { message: string; resolve: (value: boolean) => void };
export function notify(message: string, options: Omit<Notice, "id" | "message"> = {}) {
  window.dispatchEvent(new CustomEvent("studyflow-notice", { detail: { id: crypto.randomUUID(), message, ...options } }));
}
export function confirmAction(message: string): Promise<boolean> {
  return new Promise((resolve) => window.dispatchEvent(new CustomEvent("studyflow-confirm", { detail: { message, resolve } })));
}

export default function DataSyncStatus() {
  const { user } = useAuth();
  const [message, setMessage] = useState("");
  const [notices, setNotices] = useState<Notice[]>([]);
  const [confirmation, setConfirmation] = useState<Confirmation | null>(null);
  const [pending, setPending] = useState<string | null>(null);
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const failed = (event: Event) => setMessage((event as CustomEvent<string>).detail);
    const notice = (event: Event) => setNotices((previous) => [...previous, (event as CustomEvent<Notice>).detail]);
    const confirm = (event: Event) => setConfirmation((previous) => { previous?.resolve(false); return (event as CustomEvent<Confirmation>).detail; });
    const reset = (event: Event) => { if ((event as CustomEvent<boolean>).detail) setNotices([]); };
    window.addEventListener("studyflow-sync-error", failed);
    window.addEventListener("studyflow-notice", notice);
    window.addEventListener("studyflow-confirm", confirm);
    window.addEventListener("studyflow-reset-state", reset);
    return () => { window.removeEventListener("studyflow-sync-error", failed); window.removeEventListener("studyflow-notice", notice); window.removeEventListener("studyflow-confirm", confirm); window.removeEventListener("studyflow-reset-state", reset); };
  }, [user?.id]);
  useEffect(() => { const handles = notices.filter((notice) => !notice.action && !notice.error).map((notice) => setTimeout(() => setNotices((items) => items.filter((item) => item.id !== notice.id)), 8000)); return () => handles.forEach(clearTimeout); }, [notices]);
  useEffect(() => { if (confirmation && dialog.current && !dialog.current.open) dialog.current.showModal(); }, [confirmation]);
  const close = (result: boolean) => { confirmation?.resolve(result); dialog.current?.close(); setConfirmation(null); };
  return <>
    {message && <div role="alert" className="feedback-error"><p>{message}</p><button type="button" onClick={async () => { try { await retryPendingState(); setMessage(""); } catch { /* Keep the error visible. */ } }}>Retry sync</button></div>}
    <div className="feedback-stack" aria-label="Activity feedback">{notices.map((notice) => <div key={notice.id} role={notice.error ? "alert" : "status"} className="feedback-notice">
      <p>{notice.message}</p><div className="flex gap-4 mt-2">{notice.action && <button disabled={pending === notice.id} onClick={async () => {
        setPending(notice.id); try { await notice.action!.run(); setNotices((items) => items.filter((item) => item.id !== notice.id)); }
        catch (failure) { notify(failure instanceof Error ? failure.message : "Unable to complete this action. Try again.", { error: true }); }
        finally { setPending(null); }
      }}>{pending === notice.id ? "Working…" : notice.action.label}</button>}<button disabled={pending === notice.id} aria-label={`Dismiss: ${notice.message}`} onClick={() => setNotices((items) => items.filter((item) => item.id !== notice.id))}>Dismiss</button></div>
    </div>)}</div>
    {confirmation && <dialog ref={dialog} className="feedback-dialog" aria-labelledby="confirmation-title" onCancel={(event) => { event.preventDefault(); close(false); }}><h2 id="confirmation-title">Confirm data reset</h2><p>{confirmation.message}</p><div className="flex justify-end gap-4 mt-6"><button autoFocus onClick={() => close(false)}>Cancel</button><button className="text-(--danger)" onClick={() => close(true)}>Delete study data</button></div></dialog>}
  </>;
}
