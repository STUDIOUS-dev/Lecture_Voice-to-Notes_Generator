import { useMemo, useState } from 'react';
import { CircleCheck, CircleX, Eye, EyeOff, RotateCcw } from 'lucide-react';
import { asArray, toText } from '../../utils';
import EmptyState from '../EmptyState';

const LETTERS = 'ABCDEFGHIJ';

function DifficultyBadge({ value }) {
  const label = toText(value).trim();
  if (!label) return null;
  const level = label.toLowerCase();
  return <span className={`badge badge--${['easy', 'medium', 'hard'].includes(level) ? level : 'neutral'}`}>{label}</span>;
}

function normalizeMcqs(raw) {
  return asArray(raw)
    .map((q) => {
      const options = asArray(q?.options)
        .map(toText)
        .map((o) => o.replace(/^\s*[A-Ja-j][).:]\s+/, '').trim())
        .filter(Boolean);
      const ai = q?.answer_index;
      const answer = Number.isInteger(ai) && ai >= 0 && ai < options.length ? ai : null;
      return {
        question: toText(q?.question).trim(),
        options,
        answer,
        explanation: toText(q?.explanation).trim(),
        difficulty: q?.difficulty,
      };
    })
    .filter((q) => q.question);
}

function normalizeShort(raw) {
  return asArray(raw)
    .map((q) => ({
      question: toText(q?.question).trim(),
      answer: toText(q?.answer).trim(),
      difficulty: q?.difficulty,
    }))
    .filter((q) => q.question);
}

export default function QuizTab({ results }) {
  const mcqs = useMemo(() => normalizeMcqs(results?.quiz?.mcqs), [results]);
  const shortAnswers = useMemo(() => normalizeShort(results?.quiz?.short_answers), [results]);

  const [selected, setSelected] = useState({});
  const [checked, setChecked] = useState(false);
  const [revealed, setRevealed] = useState({});

  const gradable = mcqs.filter((q) => q.options.length && q.answer !== null);
  const score = mcqs.reduce(
    (acc, q, i) => acc + (q.answer !== null && selected[i] === q.answer ? 1 : 0),
    0,
  );
  const answeredCount = Object.keys(selected).length;
  const allRevealed = shortAnswers.length > 0 && shortAnswers.every((_, i) => revealed[i]);

  const reset = () => {
    setSelected({});
    setChecked(false);
  };

  if (!mcqs.length && !shortAnswers.length) {
    return (
      <div className="content-card">
        <h2 className="card-title">Quiz</h2>
        <EmptyState>No quiz was generated for this lecture.</EmptyState>
      </div>
    );
  }

  return (
    <div className="stack">
      {mcqs.length > 0 && (
        <div className="content-card">
          <div className="card-header">
            <h2 className="card-title">Multiple choice</h2>
            {gradable.length > 0 && (
              <span className="toolbar-meta">
                {answeredCount} of {mcqs.length} answered
              </span>
            )}
          </div>

          {checked && gradable.length > 0 && (
            <div className="score-banner" role="status">
              <strong>
                You scored {score} / {gradable.length}
              </strong>
              <span>({Math.round((score / gradable.length) * 100)}%)</span>
            </div>
          )}

          <ol className="quiz-list">
            {mcqs.map((q, qi) => {
              const pick = selected[qi];
              const isCorrect = checked && q.answer !== null && pick === q.answer;
              const isWrong = checked && q.answer !== null && pick !== q.answer;
              return (
                <li key={qi} className={`quiz-item ${isCorrect ? 'is-correct' : ''} ${isWrong ? 'is-wrong' : ''}`}>
                  <fieldset>
                    <legend className="quiz-question">
                      <span className="quiz-number">Q{qi + 1}.</span> {q.question}
                    </legend>
                    <DifficultyBadge value={q.difficulty} />

                    {q.options.length > 0 && (
                      <div className="option-list">
                        {q.options.map((opt, oi) => {
                          const chosen = pick === oi;
                          let state = '';
                          if (checked && q.answer !== null) {
                            if (oi === q.answer) state = 'correct';
                            else if (chosen) state = 'wrong';
                          }
                          return (
                            <label key={oi} className={`option ${chosen ? 'is-selected' : ''} ${state ? `is-${state}` : ''}`}>
                              <input
                                type="radio"
                                name={`mcq-${qi}`}
                                checked={chosen}
                                disabled={checked}
                                onChange={() => setSelected((s) => ({ ...s, [qi]: oi }))}
                              />
                              <span className="option-letter" aria-hidden="true">{LETTERS[oi] || oi + 1}</span>
                              <span className="option-text">{opt}</span>
                              {state === 'correct' && (
                                <span className="option-flag">
                                  <CircleCheck size={16} aria-hidden="true" />
                                  <span className="visually-hidden">Correct answer</span>
                                </span>
                              )}
                              {state === 'wrong' && (
                                <span className="option-flag">
                                  <CircleX size={16} aria-hidden="true" />
                                  <span className="visually-hidden">Your answer, incorrect</span>
                                </span>
                              )}
                            </label>
                          );
                        })}
                      </div>
                    )}

                    {checked && (
                      <div className="quiz-feedback">
                        {q.answer === null ? (
                          <p className="muted">No answer key was provided for this question.</p>
                        ) : (
                          <p className={isCorrect ? 'feedback-correct' : 'feedback-wrong'}>
                            {isCorrect
                              ? 'Correct!'
                              : pick === undefined
                                ? `Not answered. The correct answer is ${LETTERS[q.answer]}.`
                                : `Incorrect. The correct answer is ${LETTERS[q.answer]}.`}
                          </p>
                        )}
                        {q.explanation && <p className="explanation">{q.explanation}</p>}
                      </div>
                    )}
                  </fieldset>
                </li>
              );
            })}
          </ol>

          <div className="quiz-actions">
            {gradable.length > 0 && !checked && (
              <button type="button" className="btn-primary" onClick={() => setChecked(true)}>
                Check answers
              </button>
            )}
            {(checked || answeredCount > 0) && (
              <button type="button" className="btn-outline" onClick={reset}>
                <RotateCcw size={15} aria-hidden="true" /> Reset
              </button>
            )}
          </div>
        </div>
      )}

      {shortAnswers.length > 0 && (
        <div className="content-card">
          <div className="card-header">
            <h2 className="card-title">Short answer</h2>
            <button
              type="button"
              className="btn-outline btn-sm"
              onClick={() =>
                setRevealed(allRevealed ? {} : Object.fromEntries(shortAnswers.map((_, i) => [i, true])))
              }
            >
              {allRevealed ? 'Hide all' : 'Show all'}
            </button>
          </div>
          <ol className="quiz-list">
            {shortAnswers.map((q, i) => {
              const open = !!revealed[i];
              return (
                <li key={i} className="quiz-item">
                  <p className="quiz-question">
                    <span className="quiz-number">Q{i + 1}.</span> {q.question}
                  </p>
                  <DifficultyBadge value={q.difficulty} />
                  <div>
                    <button
                      type="button"
                      className="link-button"
                      aria-expanded={open}
                      aria-controls={`sa-answer-${i}`}
                      onClick={() => setRevealed((r) => ({ ...r, [i]: !r[i] }))}
                    >
                      {open ? <EyeOff size={15} aria-hidden="true" /> : <Eye size={15} aria-hidden="true" />}
                      {open ? 'Hide answer' : 'Show answer'}
                    </button>
                  </div>
                  <div id={`sa-answer-${i}`} hidden={!open} className="answer-box">
                    {q.answer || 'No model answer was provided.'}
                  </div>
                </li>
              );
            })}
          </ol>
        </div>
      )}
    </div>
  );
}
