import { useMemo, useState } from 'react';
import { ChevronLeft, ChevronRight, GalleryHorizontal, LayoutList } from 'lucide-react';
import { asArray, toText } from '../../utils';
import EmptyState from '../EmptyState';

export default function FlashcardsTab({ results }) {
  const cards = useMemo(
    () =>
      asArray(results?.flashcards)
        .map((c) => ({ question: toText(c?.question).trim(), answer: toText(c?.answer).trim() }))
        .filter((c) => c.question || c.answer),
    [results],
  );

  const [mode, setMode] = useState('deck');
  const [index, setIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);

  if (!cards.length) {
    return (
      <div className="content-card">
        <h2 className="card-title">Flashcards</h2>
        <EmptyState>No flashcards were generated for this lecture.</EmptyState>
      </div>
    );
  }

  const current = Math.min(index, cards.length - 1);
  const card = cards[current];

  const go = (delta) => {
    setIndex((i) => Math.max(0, Math.min(cards.length - 1, i + delta)));
    setFlipped(false);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'ArrowRight') {
      e.preventDefault();
      go(1);
    } else if (e.key === 'ArrowLeft') {
      e.preventDefault();
      go(-1);
    }
  };

  return (
    <div className="content-card">
      <div className="card-header">
        <h2 className="card-title">Flashcards</h2>
        <div className="segmented" role="group" aria-label="Flashcard view">
          <button type="button" aria-pressed={mode === 'deck'} onClick={() => setMode('deck')}>
            <GalleryHorizontal size={14} aria-hidden="true" /> Study
          </button>
          <button type="button" aria-pressed={mode === 'list'} onClick={() => setMode('list')}>
            <LayoutList size={14} aria-hidden="true" /> Show all
          </button>
        </div>
      </div>

      {mode === 'deck' ? (
        <div className="flashcard-deck" onKeyDown={handleKeyDown}>
          <button
            type="button"
            className={`flashcard ${flipped ? 'is-flipped' : ''}`}
            onClick={() => setFlipped((f) => !f)}
            aria-describedby="flashcard-help"
          >
            {/* Keyed so switching cards never animates the previous card's answer. */}
            <span className="flashcard-inner" key={current}>
              <span className="flashcard-face flashcard-front" aria-hidden={flipped}>
                <span className="flashcard-label">Question</span>
                <span className="flashcard-text">{card.question || '—'}</span>
              </span>
              <span className="flashcard-face flashcard-back" aria-hidden={!flipped}>
                <span className="flashcard-label">Answer</span>
                <span className="flashcard-text">{card.answer || '—'}</span>
              </span>
            </span>
          </button>
          <p id="flashcard-help" className="flashcard-help">
            Click or press Space to flip · Use ← → to move between cards
          </p>

          <div className="flashcard-nav">
            <button
              type="button"
              className="btn-outline btn-sm"
              onClick={() => go(-1)}
              disabled={current === 0}
            >
              <ChevronLeft size={16} aria-hidden="true" /> Previous
            </button>
            <span className="flashcard-counter" aria-live="polite">
              Card {current + 1} of {cards.length}
            </span>
            <button
              type="button"
              className="btn-outline btn-sm"
              onClick={() => go(1)}
              disabled={current === cards.length - 1}
            >
              Next <ChevronRight size={16} aria-hidden="true" />
            </button>
          </div>
        </div>
      ) : (
        <ol className="flashcard-list">
          {cards.map((c, i) => (
            <li key={i} className="flashcard-list-item">
              <p className="flashcard-list-q">
                <span className="quiz-number">Q{i + 1}.</span> {c.question || '—'}
              </p>
              <p className="flashcard-list-a">{c.answer || '—'}</p>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
