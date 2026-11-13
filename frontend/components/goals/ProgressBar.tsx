interface ProgressBarProps {
  progress: number;
}

export default function ProgressBar({
  progress,
}: ProgressBarProps) {
  const safeProgress = Math.min(
    100,
    Math.max(0, progress)
  );

  const progressColor =
    safeProgress >= 100
      ? "var(--success)"
      : safeProgress >= 70
      ? "var(--primary)"
      : safeProgress >= 40
      ? "var(--warning)"
      : "var(--danger)";

  const progressLabel =
    safeProgress >= 100
      ? "Completed"
      : safeProgress >= 70
      ? "Almost there"
      : safeProgress >= 40
      ? "Making progress"
      : "Just getting started";

  return <div className="goal-progress">
    <div className="goal-progress-heading"><span>{progressLabel}</span><strong>{safeProgress}%</strong></div>
    <div className="goal-progress-track" role="progressbar" aria-label="Goal progress" aria-valuenow={safeProgress} aria-valuemin={0} aria-valuemax={100}>
      <div className="h-full rounded-full transition-[width] duration-300 ease-out" style={{ width: `${safeProgress}%`, backgroundColor: progressColor }} />
    </div>
    <div className="goal-progress-scale"><span>0%</span><span>100%</span></div>
  </div>;
}
