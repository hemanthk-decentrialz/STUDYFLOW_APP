import { ReactNode } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faGraduationCap } from "@fortawesome/free-solid-svg-icons";

export default function AuthLayout({ children }: { children: ReactNode }) {
  return <main className="auth-page"><div className="auth-frame">
    <aside className="auth-intro" aria-label="About Studyflow">
      <div className="auth-brand"><FontAwesomeIcon icon={faGraduationCap} aria-hidden="true" /><span>Studyflow</span></div>
      <div><h2>A little structure.<br />More room to learn.</h2><p>Your courses, notes and goals, together in one thoughtful study space.</p></div>
      <span className="auth-intro-footer">Plan with purpose. Study at your pace.</span>
    </aside>
    <section className="auth-content" aria-label="Your account">{children}</section>
  </div></main>;
}
