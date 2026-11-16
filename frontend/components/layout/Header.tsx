"use client";

import { MouseEvent, useRef, useState } from "react";
import { flushSync } from "react-dom";
import { notify } from "@/components/ui/DataSyncStatus";
import { useAuth } from "@/context/AuthContext";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faBars, faArrowRight, faSun, faMoon } from "@fortawesome/free-solid-svg-icons";
import { getGreeting } from "@/utils/greetings";
import usePreferences from "@/hooks/usePreferences";
import { formatDate } from "@/utils/formatDate";

interface HeaderProps {
  onMenuClick: () => void;
  menuOpen: boolean;
}

export default function Header({
  onMenuClick, menuOpen,
}: HeaderProps) {
  const router = useRouter();
  const [signingOut, setSigningOut] = useState(false);
  const { user, logout } = useAuth();
  const { settings, setSettings, ready } = usePreferences();
  const themeTransitionPending = useRef(false);

  async function toggleTheme(event: MouseEvent<HTMLButtonElement>) {
    if (!ready || themeTransitionPending.current) return;
    const { left, top, width, height } = event.currentTarget.getBoundingClientRect();
    const x = left + width / 2;
    const y = top + height / 2;
    const endRadius = Math.hypot(Math.max(x, window.innerWidth - x), Math.max(y, window.innerHeight - y));
    let applied = false;
    const applyTheme = () => {
      if (applied) return;
      applied = true;
      flushSync(() => setSettings((current) => ({ ...current, theme: current.theme === "dark" ? "light" : "dark" })));
    };
    if (!document.startViewTransition || window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      applyTheme();
      return;
    }
    themeTransitionPending.current = true;
    try {
      const transition = document.startViewTransition(applyTheme);
      // A hidden document or interrupted capture can skip the visual transition.
      void transition.finished.catch(() => {});
      await transition.ready;
      const animation = document.documentElement.animate({
        clipPath: [`circle(0px at ${x}px ${y}px)`, `circle(${endRadius}px at ${x}px ${y}px)`],
      }, {
        duration: 420,
        easing: "cubic-bezier(0.16, 1, 0.3, 1)",
        pseudoElement: "::view-transition-new(root)",
      });
      await animation.finished;
      await transition.finished;
    } catch {
      applyTheme();
    } finally {
      themeTransitionPending.current = false;
    }
  }

  const greeting = getGreeting(settings.timeZone);
  const formattedDate = formatDate(new Date(), settings.timeZone);

  return (
    <header className="workspace-header sticky top-0 z-30 flex items-center justify-between gap-3" style={{ borderColor: "var(--border)", }}>
      {/* Left */}
      <div className="flex min-w-0 items-center gap-2 sm:gap-4">
        <button onClick={onMenuClick} aria-label={menuOpen ? "Collapse navigation" : "Open navigation"} aria-controls="studyflow-navigation" aria-expanded={menuOpen} className="icon-button rounded-xl p-3 transition-transform">
          <FontAwesomeIcon icon={faBars} className="text-lg" />
        </button>
        <div className="min-w-0">
          <h2 className="truncate text-sm font-semibold sm:text-2xl sm:font-bold" style={{ color: "var(--foreground)", }} suppressHydrationWarning>
            {greeting}
          </h2>
          <p className="header-date text-muted hidden sm:block" suppressHydrationWarning>
            {formattedDate}
          </p>
        </div>
      </div>
      {/* Right */}
      <div className="flex shrink-0 items-center gap-2 sm:gap-4">
        <button
          type="button"
          role="switch"
          aria-label="Dark mode"
          aria-checked={settings.theme === "dark"}
          title={settings.theme === "dark" ? "Late Night Cram — switch to light mode" : "Day Study — switch to dark mode"}
          disabled={!ready}
          className="header-theme-switch"
          onClick={(event) => { void toggleTheme(event); }}
        >
          <span className="header-theme-track" aria-hidden="true">
            <FontAwesomeIcon icon={faSun} className="header-theme-sun" />
            <FontAwesomeIcon icon={faMoon} className="header-theme-moon" />
            <span className="header-theme-thumb"><FontAwesomeIcon icon={settings.theme === "dark" ? faMoon : faSun} /></span>
          </span>
          <span className="header-theme-label" aria-hidden="true">{settings.theme === "dark" ? "Late Night Cram" : "Day Study"}</span>
        </button>
        <Link href="/profile" aria-label="Open your profile" className="header-profile min-w-0">
          <div className="header-avatar shrink-0">
            <p className="text-inherit" suppressHydrationWarning>
              {user?.name
                ?.split(" ")
                .map((n) => n[0])
                .join("")
                .slice(0, 2)
                .toUpperCase()}
            </p>
          </div>
          <div className="hidden max-w-40 text-left md:block">
            <p className="truncate text-xs font-semibold" style={{ color: "var(--foreground)", }} suppressHydrationWarning>
              {user?.name}
            </p>
            <p className="text-muted truncate text-[11px]" suppressHydrationWarning>
              {user?.email}
            </p>
          </div>
          <FontAwesomeIcon icon={faArrowRight} className="text-muted hidden text-xs md:block" />
        </Link>
        <button
          disabled={signingOut}
          onClick={async () => {
            setSigningOut(true);
            try {
              await logout();
              router.replace("/login");
              router.refresh();
            } catch (error) {
              notify(error instanceof Error ? error.message : "Unable to log out. Please try again.", { error: true });
            } finally { setSigningOut(false); }
          }} className="header-logout"
        >
          {signingOut ? "Signing out…" : "Logout"}
        </button>
      </div>
    </header>
  );
}
