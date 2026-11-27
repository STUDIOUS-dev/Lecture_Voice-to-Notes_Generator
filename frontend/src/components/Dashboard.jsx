import { useRef, useState } from 'react';
import {
  Calendar,
  Clock,
  Cpu,
  FileDown,
  FileText,
  Gauge,
  CircleHelp,
  Layers,
  ListChecks,
  Plus,
  Tags,
  FileCode,
} from 'lucide-react';
import { exportUrl } from '../api';
import { asArray, formatDate, formatDuration, providerLabel, toText } from '../utils';
import TranscriptTab from './tabs/TranscriptTab';
import SummaryTab from './tabs/SummaryTab';
import KeywordsTab from './tabs/KeywordsTab';
import QuizTab from './tabs/QuizTab';
import FlashcardsTab from './tabs/FlashcardsTab';
import MetricsTab from './tabs/MetricsTab';

const TABS = [
  { id: 'transcript', label: 'Transcript', Icon: FileText, Panel: TranscriptTab },
  { id: 'summary', label: 'Summary', Icon: ListChecks, Panel: SummaryTab },
  { id: 'keywords', label: 'Keywords', Icon: Tags, Panel: KeywordsTab },
  { id: 'quiz', label: 'Quiz', Icon: CircleHelp, Panel: QuizTab },
  { id: 'flashcards', label: 'Flashcards', Icon: Layers, Panel: FlashcardsTab },
  { id: 'metrics', label: 'Metrics', Icon: Gauge, Panel: MetricsTab },
];

function tabCount(id, results) {
  if (id === 'quiz') {
    return asArray(results?.quiz?.mcqs).length + asArray(results?.quiz?.short_answers).length;
  }
  if (id === 'flashcards') return asArray(results?.flashcards).length;
  return null;
}

export default function Dashboard({ results, jobId, onReset }) {
  const [active, setActive] = useState('transcript');
  const tabRefs = useRef([]);

  const filename = toText(results?.filename) || 'Untitled lecture';
  const created = formatDate(results?.created_at);
  const duration = formatDuration(results?.duration_seconds);
  const provider = providerLabel(results?.provider);

  const handleTabKeyDown = (e, index) => {
    let next = null;
    if (e.key === 'ArrowRight') next = (index + 1) % TABS.length;
    else if (e.key === 'ArrowLeft') next = (index - 1 + TABS.length) % TABS.length;
    else if (e.key === 'Home') next = 0;
    else if (e.key === 'End') next = TABS.length - 1;
    if (next === null) return;
    e.preventDefault();
    setActive(TABS[next].id);
    tabRefs.current[next]?.focus();
  };

  return (
    <div className="dashboard-view">
      <section className="dashboard-header" aria-labelledby="view-heading">
        <div className="dashboard-title">
          <div className="dashboard-title-text">
            <span className="eyebrow">Lecture notes</span>
            <h1 id="view-heading" tabIndex={-1} title={filename}>
              {filename}
            </h1>
            <ul className="dashboard-meta" aria-label="Lecture details">
              {created && (
                <li>
                  <Calendar size={14} aria-hidden="true" /> {created}
                </li>
              )}
              {duration && (
                <li>
                  <Clock size={14} aria-hidden="true" /> {duration}
                </li>
              )}
              {provider && (
                <li>
                  <Cpu size={14} aria-hidden="true" /> {provider}
                </li>
              )}
            </ul>
          </div>
          {jobId && (
            <div className="dashboard-actions">
              <a className="btn-outline" href={exportUrl(jobId, 'pdf')} download>
                <FileDown size={15} aria-hidden="true" /> PDF
              </a>
              <a className="btn-outline" href={exportUrl(jobId, 'md')} download>
                <FileCode size={15} aria-hidden="true" /> Markdown
              </a>
              <button type="button" className="btn-secondary" onClick={onReset}>
                <Plus size={15} aria-hidden="true" /> New upload
              </button>
            </div>
          )}
        </div>

        <div className="tabs" role="tablist" aria-label="Lecture sections">
          {TABS.map((tab, i) => {
            const { id, label, Icon } = tab;
            const selected = active === id;
            const count = tabCount(id, results);
            return (
              <button
                key={id}
                ref={(el) => {
                  tabRefs.current[i] = el;
                }}
                type="button"
                role="tab"
                id={`tab-${id}`}
                aria-selected={selected}
                aria-controls={`panel-${id}`}
                tabIndex={selected ? 0 : -1}
                className={`tab ${selected ? 'active' : ''}`}
                onClick={() => setActive(id)}
                onKeyDown={(e) => handleTabKeyDown(e, i)}
              >
                <Icon size={15} aria-hidden="true" />
                {label}
                {count ? <span className="tab-count">{count}</span> : null}
              </button>
            );
          })}
        </div>
      </section>

      {TABS.map((tab) => {
        const { id, Panel } = tab;
        return (
        <div
          key={id}
          role="tabpanel"
          id={`panel-${id}`}
          aria-labelledby={`tab-${id}`}
          hidden={active !== id}
          tabIndex={0}
          className="tab-panel"
        >
          <Panel results={results} />
        </div>
        );
      })}
    </div>
  );
}
