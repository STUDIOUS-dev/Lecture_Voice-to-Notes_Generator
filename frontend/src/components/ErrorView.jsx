import { CircleAlert, RefreshCw, ArrowRight } from 'lucide-react';

export default function ErrorView({ title, message, onReset, onRetry }) {
  return (
    <section className="state-view" role="alert">
      <div className="state-icon state-icon--error">
        <CircleAlert size={32} aria-hidden="true" />
      </div>
      <h1 id="view-heading" className="state-title" tabIndex={-1}>
        {title || 'Something went wrong'}
      </h1>
      <p className="state-text">{message || 'An unexpected error occurred.'}</p>
      <div className="state-actions">
        {onRetry && (
          <button type="button" className="btn-outline" onClick={onRetry}>
            <RefreshCw size={15} aria-hidden="true" /> Try again
          </button>
        )}
        <button type="button" className="btn-primary" onClick={onReset}>
          Upload another file <ArrowRight size={16} aria-hidden="true" />
        </button>
      </div>
    </section>
  );
}
