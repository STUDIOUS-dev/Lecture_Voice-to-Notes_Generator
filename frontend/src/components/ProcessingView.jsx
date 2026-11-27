import { Check, LoaderCircle, WifiOff } from 'lucide-react';
import useJobPolling from '../hooks/useJobPolling';
import { isNum, toText } from '../utils';

const STEPS = [
  { label: 'Uploading', hint: 'Sending your recording to the server' },
  { label: 'Transcribing', hint: 'Converting speech to text' },
  { label: 'Generating notes', hint: 'Summary, keywords, topics, quiz and flashcards' },
  { label: 'Finalizing', hint: 'Scoring quality and preparing your results' },
];

// Progress thresholds at which each step starts (server progress, 0-100).
const STEP_STARTS = [0, 10, 45, 90];

function stepFromText(text) {
  const t = text.toLowerCase();
  if (/final|metric|evaluat|scor|export|sav|complet|done/.test(t)) return 3;
  if (/summar|keyword|topic|segment|quiz|flashcard|analy|generat|clean|note|llm/.test(t)) return 2;
  if (/transcri|speech|whisper|audio|convert|preprocess|load/.test(t)) return 1;
  return -1;
}

function stepFromProgress(progress) {
  let idx = 0;
  STEP_STARTS.forEach((start, i) => {
    if (progress >= start) idx = i;
  });
  return idx;
}

const clamp = (n) => Math.max(0, Math.min(100, Math.round(n)));

export default function ProcessingView({ phase, jobId, uploadPercent, onDone, onError }) {
  const { status, retrying } = useJobPolling(phase === 'processing' ? jobId : null, {
    onDone,
    onError,
  });

  const serverProgress = isNum(status?.progress) ? clamp(status.progress) : 0;
  const stepText = toText(status?.step);
  const queued = status?.status === 'queued';

  let active;
  let overall;
  let detail;
  if (phase === 'uploading') {
    active = 0;
    overall = clamp((uploadPercent || 0) * 0.1);
    detail = `Uploading… ${clamp(uploadPercent || 0)}%`;
  } else if (phase === 'loading') {
    active = 3;
    overall = 100;
    detail = 'Loading your results…';
  } else {
    active = Math.max(1, stepFromProgress(serverProgress), stepFromText(stepText));
    overall = Math.max(10, serverProgress);
    detail = stepText || (queued ? 'Waiting in queue…' : status ? 'Processing…' : 'Checking job status…');
  }

  return (
    <section className="processing-view" aria-labelledby="view-heading">
      <div className="processing-card">
        <LoaderCircle size={40} className="spinner" aria-hidden="true" />
        <h1 id="view-heading" className="state-title" tabIndex={-1}>
          Processing your lecture
        </h1>
        <p className="state-text">
          Longer recordings can take several minutes. You can keep this tab open — or bookmark
          this page and come back later.
        </p>

        <div className="progress-block">
          <div className="progress-labels">
            <span className="progress-detail">{detail}</span>
            <span className="progress-percent">{overall}%</span>
          </div>
          <div
            className="progress-track"
            role="progressbar"
            aria-label="Overall progress"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={overall}
          >
            <div className="progress-fill" style={{ width: `${overall}%` }} />
          </div>
        </div>

        <p className="visually-hidden" role="status" aria-live="polite">
          {`Step ${active + 1} of ${STEPS.length}: ${STEPS[active].label}. ${detail}`}
        </p>

        <ol className="step-list">
          {STEPS.map((s, i) => {
            const state = i < active ? 'done' : i === active ? 'active' : 'pending';
            return (
              <li key={s.label} className={`step step--${state}`} aria-current={state === 'active' ? 'step' : undefined}>
                <span className="step-marker" aria-hidden="true">
                  {state === 'done' ? (
                    <Check size={14} />
                  ) : state === 'active' ? (
                    <LoaderCircle size={14} className="spinner" />
                  ) : (
                    i + 1
                  )}
                </span>
                <span className="step-body">
                  <span className="step-label">
                    {s.label}
                    <span className="visually-hidden">
                      {state === 'done' ? ' (complete)' : state === 'active' ? ' (in progress)' : ' (pending)'}
                    </span>
                  </span>
                  <span className="step-hint">{s.hint}</span>
                </span>
              </li>
            );
          })}
        </ol>

        {retrying && (
          <p className="notice" role="status">
            <WifiOff size={15} aria-hidden="true" />
            Connection hiccup — retrying…
          </p>
        )}
      </div>
    </section>
  );
}
