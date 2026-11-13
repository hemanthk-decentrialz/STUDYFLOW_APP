"use client";

import { useState } from "react";
import { notify } from "@/components/ui/DataSyncStatus";
import { useAuth } from "@/context/AuthContext";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faBars, faArrowRight } from "@fortawesome/free-solid-svg-icons";
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
  const { settings } = usePreferences();
  const greeting = getGreeting(settings.timeZone);
  const formattedDate = formatDate(new Date(), settings.timeZone);

  return (
    <header className="workspace-header sticky top-0 z-30 flex items-center justify-between gap-3" style={{ borderColor: "var(--border)", }}>
      {/* Left */}
      <div className="flex min-w-0 items-center gap-2 sm:gap-4">
        <button onClick={onMenuClick} aria-label={menuOpen ? "Collapse navigation" : "Open navigation"} aria-controls="studyflow-navigation" aria-expanded={menuOpen} className="icon-button rounded-xl p-3 transition">
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
