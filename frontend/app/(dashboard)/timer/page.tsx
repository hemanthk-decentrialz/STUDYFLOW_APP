import FocusHistory from "@/components/timer/FocusHistory";
import StudyTimer from "@/components/timer/StudyTimer";

export default function TimerPage() {
  return <div className="timer-page"><div className="standalone-heading"><h1>Focus timer</h1><p>One session at a time.</p></div><StudyTimer /><FocusHistory /></div>;
}
