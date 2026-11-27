import { useDeferredValue, useMemo, useState } from 'react';
import { Search, X } from 'lucide-react';
import { asArray, escapeRegExp, formatTimestamp, isNum, toText } from '../../utils';
import CopyButton from '../CopyButton';
import Highlight from '../Highlight';
import EmptyState from '../EmptyState';

export default function TranscriptTab({ results }) {
  const cleanText = (toText(results?.cleaned_text) || toText(results?.transcript?.text)).trim();
  const segments = useMemo(
    () =>
      asArray(results?.transcript?.segments)
        .map((s) => ({
          start: isNum(s?.start) ? s.start : null,
          end: isNum(s?.end) ? s.end : null,
          text: toText(s?.text).trim(),
        }))
        .filter((s) => s.text),
    [results],
  );
  const useHours = segments.some((s) => (s.end ?? s.start ?? 0) >= 3600);

  const [mode, setMode] = useState(cleanText || !segments.length ? 'text' : 'segments');
  const [query, setQuery] = useState('');
  const deferredQuery = useDeferredValue(query.trim());

  const regex = useMemo(
    () => (deferredQuery ? new RegExp(`(${escapeRegExp(deferredQuery)})`, 'gi') : null),
    [deferredQuery],
  );

  const visibleSegments = useMemo(
    () => (regex ? segments.filter((s) => s.text.search(regex) !== -1) : segments),
    [segments, regex],
  );

  const matchCount = useMemo(() => {
    if (!regex) return 0;
    const source = mode === 'text' ? cleanText : segments.map((s) => s.text).join('\n');
    return (source.match(regex) || []).length;
  }, [regex, mode, cleanText, segments]);

  const copyText =
    mode === 'text'
      ? cleanText
      : segments
          .map((s) => `[${formatTimestamp(s.start, useHours) || '--:--'}] ${s.text}`)
          .join('\n');

  if (!cleanText && !segments.length) {
    return (
      <div className="content-card">
        <h2 className="card-title">Transcript</h2>
        <EmptyState>No transcript was generated for this lecture.</EmptyState>
      </div>
    );
  }

  return (
    <div className="content-card">
      <div className="card-header">
        <h2 className="card-title">Transcript</h2>
        <div className="segmented" role="group" aria-label="Transcript view">
          <button
            type="button"
            aria-pressed={mode === 'text'}
            onClick={() => setMode('text')}
            disabled={!cleanText}
          >
            Clean text
          </button>
          <button
            type="button"
            aria-pressed={mode === 'segments'}
            onClick={() => setMode('segments')}
            disabled={!segments.length}
          >
            Timestamped
          </button>
        </div>
      </div>

      <div className="toolbar">
        <div className="search-field">
          <Search size={16} aria-hidden="true" className="search-icon" />
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search transcript"
            aria-label="Search transcript"
          />
          {query && (
            <button
              type="button"
              className="icon-button search-clear"
              onClick={() => setQuery('')}
              aria-label="Clear search"
            >
              <X size={14} aria-hidden="true" />
            </button>
          )}
        </div>
        <span className="toolbar-meta" aria-live="polite">
          {deferredQuery ? `${matchCount} match${matchCount === 1 ? '' : 'es'}` : ''}
        </span>
        <CopyButton text={copyText} label="Copy" />
      </div>

      {mode === 'text' ? (
        <div className="scrollable-content transcript-text">
          <Highlight text={cleanText} regex={regex} />
        </div>
      ) : (
        <ol className="scrollable-content segment-list">
          {visibleSegments.length ? (
            visibleSegments.map((s, i) => (
              <li key={`${s.start}-${i}`} className="segment-row">
                <time className="timestamp">
                  {formatTimestamp(s.start, useHours) || '--:--'}
                </time>
                <span className="segment-text">
                  <Highlight text={s.text} regex={regex} />
                </span>
              </li>
            ))
          ) : (
            <li className="empty-state">No segments match “{deferredQuery}”.</li>
          )}
        </ol>
      )}
    </div>
  );
}
