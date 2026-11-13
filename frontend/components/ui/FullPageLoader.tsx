interface FullPageLoaderProps {
  label?: string;
  defer?: boolean;
}

export default function FullPageLoader({
  label = "Loading Studyflow...",
  defer = false,
}: FullPageLoaderProps) {
  return (
    <main className="flex min-h-screen items-center justify-center bg-(--background) px-6" aria-busy="true">
      <div className={`study-loader-content flex flex-col items-center gap-4 text-center${defer ? " study-loader-delayed" : ""}`}>
        <div className="study-loader-terminal" role="progressbar" aria-label={label}>
          <p className="study-loader-heading" aria-hidden="true">Studyflow / Please stand by</p>
          <div className="study-loader-segments" aria-hidden="true">
            <span>[</span>
            {Array.from({ length: 10 }, (_, index) => <span key={index} className="study-loader-segment" />)}
            <span>]</span>
          </div>
          <p className="study-loader-caption" aria-hidden="true">LOADING...</p>
        </div>
        <p role="status">{label}</p>
      </div>
    </main>
  );
}
