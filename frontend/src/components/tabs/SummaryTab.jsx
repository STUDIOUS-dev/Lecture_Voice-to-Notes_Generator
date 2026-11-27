import { asArray, toText } from '../../utils';
import EmptyState from '../EmptyState';

export default function SummaryTab({ results }) {
  const summary = results?.summary && typeof results.summary === 'object' ? results.summary : {};
  const overview = (typeof results?.summary === 'string' ? results.summary : toText(summary.overview)).trim();
  const keyPoints = asArray(summary.key_points).map(toText).filter(Boolean);
  const concepts = asArray(summary.important_concepts).map(toText).filter(Boolean);

  return (
    <div className="stack">
      <div className="content-card">
        <h2 className="card-title">Overview</h2>
        {overview ? <p className="prose">{overview}</p> : <EmptyState>No overview was generated.</EmptyState>}
      </div>
      <div className="grid-2">
        <div className="content-card">
          <h2 className="card-title">Key points</h2>
          {keyPoints.length ? (
            <ol className="numbered-list">
              {keyPoints.map((pt, i) => (
                <li key={i}>{pt}</li>
              ))}
            </ol>
          ) : (
            <EmptyState>No key points were generated.</EmptyState>
          )}
        </div>
        <div className="content-card">
          <h2 className="card-title">Important concepts</h2>
          {concepts.length ? (
            <ul className="concept-list">
              {concepts.map((c, i) => (
                <li key={i}>{c}</li>
              ))}
            </ul>
          ) : (
            <EmptyState>No important concepts were identified.</EmptyState>
          )}
        </div>
      </div>
    </div>
  );
}
