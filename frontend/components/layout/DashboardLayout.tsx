"use client";

import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from "react";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faHouse, faCalendarDays, faClock, faBars } from "@fortawesome/free-solid-svg-icons";

import Header from "./Header";
import Sidebar from "./Sidebar";
import StudyNotifications from "@/components/timer/StudyNotifications";
import TimerTicker from "@/components/timer/TimerTicker";
import DataResetMonitor from "@/components/ui/DataResetMonitor";
import DataSyncStatus from "@/components/ui/DataSyncStatus";

interface DashboardLayoutProps {
  children: React.ReactNode;
}

const desktopQuery = "(min-width: 1024px)";
const subscribeDesktop = (callback: () => void) => {
  const media = window.matchMedia(desktopQuery);
  media.addEventListener("change", callback);
  return () => media.removeEventListener("change", callback);
};

export default function DashboardLayout({
  children,
}: DashboardLayoutProps) {
  const [desktopCollapsed, setDesktopCollapsed] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  const isDesktop = useSyncExternalStore(subscribeDesktop, () => window.matchMedia(desktopQuery).matches, () => false);
  const mobileOpen = isSidebarOpen && !isDesktop;
  const navigationTrigger = useRef<HTMLElement | null>(null);
  const openSidebar = () => { if (isDesktop) { setDesktopCollapsed((value) => !value); return; } navigationTrigger.current = document.activeElement as HTMLElement; setIsSidebarOpen(true); };
  const closeSidebar = useCallback(() => {
    setIsSidebarOpen(false);
    requestAnimationFrame(() => { if (navigationTrigger.current?.offsetParent !== null) navigationTrigger.current?.focus(); });
  }, []);
  const pathname = usePathname();
  useEffect(() => {
    const media = window.matchMedia(desktopQuery);
    const changed = () => setIsSidebarOpen(false);
    media.addEventListener("change", changed);
    return () => media.removeEventListener("change", changed);
  }, []);
  useEffect(() => {
    document.body.style.overflow = mobileOpen ? "hidden" : "";

    return () => {
      document.body.style.overflow = "";
    };
  }, [mobileOpen]);

  return (
    <div
      className={`flex min-h-screen${desktopCollapsed ? " sidebar-collapsed" : ""}`}
      style={{
        background: "var(--background)",
        color: "var(--foreground)",
      }}
    >
      <Sidebar
        isOpen={isSidebarOpen}
        isDesktop={isDesktop}
        desktopCollapsed={desktopCollapsed}
        onClose={closeSidebar}
      />

      {mobileOpen && (
        <div
          onClick={closeSidebar}
          className="fixed inset-0 z-40 bg-(--overlay) backdrop-blur-sm"
        />
      )}

      {/* Main Content */}

      <div inert={mobileOpen} className="study-main flex min-w-0 flex-1 flex-col">
        <Header
          onMenuClick={openSidebar}
          menuOpen={isDesktop ? !desktopCollapsed : mobileOpen}
        />

        <main
          className="page-container flex-1"
        >
          <DataSyncStatus />
          {children}
        </main>
      </div>

      <nav className="study-mobile-nav" aria-label="Quick navigation" inert={mobileOpen}>
        {[{ href: "/", label: "Today", icon: faHouse }, { href: "/planner", label: "Planner", icon: faCalendarDays }, { href: "/timer", label: "Focus", icon: faClock }].map((item) => <Link key={item.href} href={item.href} aria-current={pathname === item.href ? "page" : undefined}><FontAwesomeIcon icon={item.icon} /><span>{item.label}</span></Link>)}
        <button aria-label="More navigation" aria-expanded={mobileOpen} aria-controls="studyflow-navigation" onClick={openSidebar}><FontAwesomeIcon icon={faBars} /><span>More</span></button>
      </nav>
      <DataResetMonitor />
      <TimerTicker />
      <StudyNotifications />
    </div>
  );
}
