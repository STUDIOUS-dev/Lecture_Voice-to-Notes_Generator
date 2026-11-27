import { Clock } from 'lucide-react';
import { asArray, formatTimestamp, isNum, toText } from '../../utils';
import EmptyState from '../EmptyState';

export default function KeywordsTab({ results }) {
  const keywords = [...new Set(asArray(results?.keywords).map(toText).map((k) => k.trim()).filter(Boolean))];
  const topics = asArray(results?.segments)
    .map((s) => ({
      title: toText(s?.title).trim(),
      content: toText(s?.content).trim(),
      start: isNum(s?.start) ? s.start : null,
    }))
    .filter((s) => s.title || s.content);

  return (
    <div className="stack">
      <div className="content-card">
        <h2 className="card-title">Keywords</h2>
        {keywords.length ? (
          <ul className="tags-container" aria-label="Keywords">
            {keywords.map((kw) => (
              <li className="tag" key={kw}>
                {kw}
              </li>
            ))}
          </ul>
        ) : (
          <EmptyState>No keywords were extracted.</EmptyState>
        )}
      </div>

      <div className="content-card">
        <h2 className="card-title">Topic sections</h2>
        {topics.length ? (
          <ol className="topic-list">
            {topics.map((t, i) => (
              <li key={i} className="topic-item">
                <div className="topic-head">
                  <span className="topic-index" aria-hidden="true">{i + 1}</span>
                  <h3 className="topic-title">{t.title || `Section ${i + 1}`}</h3>
                  {t.start != null && (
                    <span className="badge">
                      <Clock size={12} aria-hidden="true" />
                      <span className="visually-hidden">Starts at </span>
                      {formatTimestamp(t.start)}
                    </span>
                  )}
                </div>
                {t.content && <p className="prose">{t.content}</p>}
              </li>
            ))}
          </ol>
        ) : (
          <EmptyState>No topic sections were identified.</EmptyState>
        )}
      </div>
    </div>
  );
}
