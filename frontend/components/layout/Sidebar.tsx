"use client";
import { useEffect, useRef } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faHouse, faCalendarDays, faNoteSticky, faClock, faBullseye, faGear, faUser, faXmark, faGraduationCap, faBookOpen } from "@fortawesome/free-solid-svg-icons";
const groups = [
  { title: "Plan & focus", items: [
    { title: "Today", href: "/", icon: faHouse },
    { title: "Planner", href: "/planner", icon: faCalendarDays },
    { title: "Goals", href: "/goals", icon: faBullseye },
    { title: "Focus timer", href: "/timer", icon: faClock },
  ] },
  { title: "Study library", items: [
    { title: "Courses", href: "/courses", icon: faBookOpen },
    { title: "Notes", href: "/notes", icon: faNoteSticky },
  ] },
  { title: "Account", items: [
    { title: "Profile", href: "/profile", icon: faUser },
    { title: "Settings", href: "/settings", icon: faGear },
  ] },
];
export default function Sidebar({ isOpen, isDesktop, desktopCollapsed, onClose }: {
  isOpen: boolean; isDesktop: boolean; desktopCollapsed: boolean; onClose: () => void;
}) {
  const pathname = usePathname();
  const { user } = useAuth();
  const previousPath = useRef(pathname);
  useEffect(() => { if (previousPath.current !== pathname) { previousPath.current = pathname; onClose(); } }, [pathname, onClose]);
  const panel = useRef<HTMLElement>(null);
  const mobileOpen = isOpen && !isDesktop;
  useEffect(() => {
    if (!mobileOpen) return;
    const previous = document.activeElement as HTMLElement | null;
    const element = panel.current!;
    const focusable = () => [...element.querySelectorAll<HTMLElement>('a[href], button:not(:disabled)')];
    focusable()[0]?.focus();
    const keydown = (event: KeyboardEvent) => {
      if (event.key === "Escape") { event.preventDefault(); onClose(); }
      if (event.key === "Tab") {
        const nodes = focusable(), first = nodes[0], last = nodes[nodes.length - 1];
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
      }
    };
    element.addEventListener("keydown", keydown);
    return () => { element.removeEventListener("keydown", keydown); previous?.focus(); };
  }, [mobileOpen, onClose]);
  return <aside ref={panel} id="studyflow-navigation" className={`study-sidebar${mobileOpen ? " is-open" : ""}`}
    inert={isDesktop ? desktopCollapsed : !mobileOpen} role={mobileOpen ? "dialog" : undefined}
    aria-modal={mobileOpen ? true : undefined} aria-label="Studyflow navigation">
    <div className="study-sidebar-brand"><Link href="/" onClick={onClose} aria-label="Studyflow Today"><FontAwesomeIcon icon={faGraduationCap} /><span>Studyflow</span></Link>
      <button className="icon-button lg:hidden p-2" onClick={onClose} aria-label="Close navigation"><FontAwesomeIcon icon={faXmark} /></button></div>
    <nav aria-label="Main navigation">{groups.map((group) => <div className="study-nav-group" key={group.title}><p>{group.title}</p>{group.items.map((item) => <Link key={item.href} href={item.href} onClick={onClose} aria-current={pathname === item.href ? "page" : undefined}><FontAwesomeIcon icon={item.icon} /><span>{item.title}</span></Link>)}</div>)}</nav>
    <div className="study-sidebar-account"><span>{user?.name?.slice(0, 1).toUpperCase()}</span><div><strong>{user?.name}</strong><p>Personal workspace</p></div></div>
  </aside>;
}
