import { formatDuration, isNum, providerLabel } from '../../utils';

const fixed = (n, d) => (isNum(n) ? n.toFixed(d) : null);

function MetricBox({ label, value, explanation, meter, better }) {
  const display = value ?? 'N/A';
  return (
    <div className={`metric-box ${value == null ? 'is-empty' : ''}`}>
      <span className="metric-label">{label}</span>
      <span className="metric-value">{display}</span>
      {meter != null && (
        <span className="meter" aria-hidden="true">
          <span className="meter-fill" style={{ width: `${Math.round(meter * 100)}%` }} />
        </span>
      )}
      {better && value != null && <span className="metric-hint">{better}</span>}
      <span className="metric-explain">{explanation}</span>
    </div>
  );
}

const unit = (n) => (isNum(n) && n >= 0 && n <= 1 ? n : null);

export default function MetricsTab({ results }) {
  const m = results?.metrics && typeof results.metrics === 'object' ? results.metrics : {};

  const quality = [
    {
      label: 'Word error rate',
      value: fixed(m.wer, 3),
      meter: unit(m.wer),
      better: 'Lower is better',
      explanation: 'Share of words the transcript got wrong compared with a reference transcript.',
    },
    {
      label: 'ROUGE-1',
      value: fixed(m.rouge1, 3),
      meter: unit(m.rouge1),
      better: 'Higher is better',
      explanation: 'Single-word overlap between the summary and the source text.',
    },
    {
      label: 'ROUGE-L',
      value: fixed(m.rougeL, 3),
      meter: unit(m.rougeL),
      better: 'Higher is better',
      explanation: 'Longest shared word sequence between the summary and the source text.',
    },
    {
      label: 'Compression ratio',
      value: fixed(m.compression_ratio, 2),
      explanation: 'How much the summary condenses the full transcript.',
    },
  ];

  const info = [
    {
      label: 'Word count',
      value: isNum(m.word_count) ? Math.round(m.word_count).toLocaleString() : null,
      explanation: 'Words in the transcript.',
    },
    {
      label: 'Duration',
      value: formatDuration(results?.duration_seconds) || null,
      explanation: 'Length of the uploaded recording.',
    },
    {
      label: 'Provider',
      value: providerLabel(results?.provider) || null,
      explanation: 'Engine used for transcription and note generation.',
    },
  ];

  return (
    <div className="stack">
      <div className="content-card">
        <h2 className="card-title">Quality metrics</h2>
        <div className="metrics-grid">
          {quality.map((q) => (
            <MetricBox key={q.label} {...q} />
          ))}
        </div>
        <p className="footnote">
          N/A means the metric could not be computed for this lecture (for example, no reference
          transcript was available).
        </p>
      </div>
      <div className="content-card">
        <h2 className="card-title">Lecture info</h2>
        <div className="metrics-grid">
          {info.map((q) => (
            <MetricBox key={q.label} {...q} />
          ))}
        </div>
      </div>
    </div>
  );
}
