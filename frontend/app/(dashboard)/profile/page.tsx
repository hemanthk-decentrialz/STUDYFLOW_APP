"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faArrowRight, faArrowRightFromBracket, faCalendarDays, faCheck,
  faShieldHalved, faSliders, faUser,
} from "@fortawesome/free-solid-svg-icons";
import usePreferences from "@/hooks/usePreferences";
import Button from "@/components/ui/Button";
import { useAuth } from "@/context/AuthContext";

export default function ProfilePage() {
  const { settings } = usePreferences();
  const { user, updateProfile, logout } = useAuth();
  const router = useRouter();
  const [draftName, setDraftName] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [signingOut, setSigningOut] = useState(false);
  const [notice, setNotice] = useState<{ kind: "success" | "error"; message: string } | null>(null);

  if (!user) return null;
  const name = draftName ?? user.name;
  const changed = name.trim() !== user.name;
  const initials = user.name.split(/\s+/).filter(Boolean).map((part) => part[0]).slice(0, 2).join("").toUpperCase();
  const joined = new Intl.DateTimeFormat("en", { timeZone: settings.timeZone, month: "long", day: "numeric", year: "numeric" })
    .format(new Date(user.createdAt));

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!changed || saving) return;
    if (!name.trim()) {
      setNotice({ kind: "error", message: "Please enter a display name." });
      return;
    }
    setSaving(true);
    setNotice(null);
    try {
      await updateProfile(name.trim());
      setDraftName(null);
      setNotice({ kind: "success", message: "Your profile has been updated." });
    } catch (error) {
      setNotice({ kind: "error", message: error instanceof Error ? error.message : "Your changes could not be saved. Please try again." });
    } finally { setSaving(false); }
  }

  async function signOut() {
    setSigningOut(true);
    setNotice(null);
    try {
      await logout();
      router.replace("/login");
      router.refresh();
    } catch (error) {
      setNotice({ kind: "error", message: error instanceof Error ? error.message : "Unable to sign out. Please try again." });
    } finally { setSigningOut(false); }
  }

  return (
    <div className="profile-page mx-auto max-w-5xl space-y-7 pb-8">
      <div>
        <p className="profile-eyebrow">YOUR WORKSPACE</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">Your profile</h1>
        <p className="text-muted mt-3 max-w-xl text-sm leading-6">A little about you. Manage how you appear in Studyflow and keep your account details close.</p>
      </div>

      <section className="profile-panel overflow-hidden" aria-label="Profile overview">
        <div className="profile-cover" aria-hidden="true"><span /><span /><span /></div>
        <div className="relative flex flex-wrap items-end gap-5 px-6 pb-6 sm:px-8">
          <div className="profile-avatar -mt-8 shrink-0" aria-label={`Initials for ${user.name}`}>{initials}</div>
          <div className="min-w-0 flex-1 pt-4">
            <h2 className="break-words text-xl font-semibold tracking-tight sm:text-2xl">{user.name}</h2>
            <p className="text-muted mt-1 break-all text-sm">{user.email}</p>
          </div>
          <span className="profile-member-label basis-full sm:basis-auto"><span aria-hidden="true" /> Personal workspace</span>
        </div>
      </section>

      {notice && <div className={`profile-notice ${notice.kind === "error" ? "profile-notice-error" : ""}`}
        role={notice.kind === "error" ? "alert" : "status"}>
        {notice.kind === "success" && <FontAwesomeIcon icon={faCheck} aria-hidden="true" />}
        <span>{notice.message}</span>
      </div>}

      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_300px]">
        <section className="profile-panel min-w-0" aria-labelledby="personal-details-heading">
          <div className="profile-section-heading">
            <span className="profile-icon"><FontAwesomeIcon icon={faUser} aria-hidden="true" /></span>
            <div><h2 id="personal-details-heading" className="font-semibold">Personal information</h2>
              <p className="text-muted mt-1 text-sm">The details that make this workspace yours.</p></div>
          </div>
          <form onSubmit={save} aria-busy={saving}>
            <fieldset disabled={saving || signingOut} className="space-y-6 px-6 py-6 sm:px-8">
              <div>
                <label htmlFor="profile-name" className="mb-2 block text-sm font-medium">Display name</label>
                <input id="profile-name" name="name" autoComplete="name" required maxLength={200}
                  className="profile-input" value={name} aria-describedby="profile-name-help"
                  onChange={(event) => { setDraftName(event.target.value); setNotice(null); }} />
                <p id="profile-name-help" className="text-muted mt-2 text-xs leading-5">This name appears throughout your workspace.</p>
              </div>
              <div>
                <label htmlFor="profile-email" className="mb-2 block text-sm font-medium">Email address</label>
                <input id="profile-email" type="email" name="email" autoComplete="email" readOnly
                  className="profile-input profile-readonly" value={user.email} aria-describedby="profile-email-help" />
                <p id="profile-email-help" className="text-muted mt-2 text-xs leading-5">Your sign-in address.</p>
              </div>
            </fieldset>
            <div className="profile-form-footer">
              <p className="text-muted text-xs">{saving ? "Saving your changes…" : changed ? "You have unsaved changes." : "Your profile is up to date."}</p>
              <div className="flex gap-2">
                <Button type="button" variant="secondary" className="profile-action" disabled={saving || signingOut || draftName === null}
                  onClick={() => { setDraftName(null); setNotice(null); }}>Cancel</Button>
                <Button type="submit" className="profile-action profile-save" loading={saving} disabled={!changed || signingOut}>Save changes</Button>
              </div>
            </div>
          </form>
        </section>

        <div className="min-w-0 space-y-6">
          <section className="profile-panel p-6" aria-labelledby="account-heading">
            <h2 id="account-heading" className="font-semibold">Account details</h2>
            <dl className="mt-6 space-y-5">
              <div className="flex gap-3">
                <FontAwesomeIcon icon={faCalendarDays} className="text-muted mt-1 w-4 shrink-0" aria-hidden="true" />
                <div><dt className="text-muted text-xs">Member since</dt><dd className="mt-1 text-sm">{joined}</dd></div>
              </div>
            </dl>
            <Link href="/settings" className="profile-settings-link mt-6">
              <span className="flex items-center gap-2"><FontAwesomeIcon icon={faSliders} aria-hidden="true" /> Preferences</span>
              <FontAwesomeIcon icon={faArrowRight} aria-hidden="true" />
            </Link>
          </section>

          <section className="profile-panel p-6" aria-labelledby="sign-in-heading">
            <span className="profile-icon mb-4"><FontAwesomeIcon icon={faShieldHalved} aria-hidden="true" /></span>
            <h2 id="sign-in-heading" className="font-semibold">Your sign-in</h2>
            <p className="text-muted mt-3 text-sm leading-6">Refreshing keeps this tab signed in. A fresh visit asks you to sign in again.</p>
            <p className="text-muted mt-3 text-xs leading-5">Using a shared device? Sign out when you are finished.</p>
            <Button type="button" variant="secondary" className="profile-action profile-signout mt-5" onClick={signOut}
              loading={signingOut} disabled={saving}>
              <FontAwesomeIcon icon={faArrowRightFromBracket} aria-hidden="true" /> Sign out
            </Button>
          </section>
        </div>
      </div>
    </div>
  );
}
