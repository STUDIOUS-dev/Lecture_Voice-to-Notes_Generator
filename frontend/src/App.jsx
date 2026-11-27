import { useCallback, useEffect, useRef, useState } from 'react';
import { Plus } from 'lucide-react';
import { getConfig, getResults, uploadAudio } from './api';
import { getJobIdFromUrl, setJobIdInUrl, toText } from './utils';
import ErrorBoundary from './components/ErrorBoundary';
import UploadView from './components/UploadView';
import ProcessingView from './components/ProcessingView';
import ErrorView from './components/ErrorView';
import Dashboard from './components/Dashboard';
import Footer from './components/Footer';
import './App.css';

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const RESULT_ATTEMPTS = 3;

// view: 'upload' | 'uploading' | 'processing' | 'loading' | 'error' | 'done'
function App() {
  const [jobId, setJobId] = useState(() => getJobIdFromUrl());
  const [view, setView] = useState(() => (getJobIdFromUrl() ? 'processing' : 'upload'));
  const [config, setConfig] = useState(null);
  const [uploadPercent, setUploadPercent] = useState(0);
  const [uploadError, setUploadError] = useState('');
  const [error, setError] = useState(null);
  const [results, setResults] = useState(null);

  // Incremented on every reset so late responses from an abandoned run are ignored.
  const runRef = useRef(0);
  const firstRender = useRef(true);

  useEffect(() => {
    const controller = new AbortController();
    getConfig({ signal: controller.signal })
      .then((data) => setConfig(data && typeof data === 'object' ? data : null))
      .catch(() => {
        // Config is optional: fall back to server-side validation only.
      });
    return () => controller.abort();
  }, []);

  // Move focus to the new view's heading so screen readers follow along.
  useEffect(() => {
    if (firstRender.current) {
      firstRender.current = false;
      return;
    }
    window.scrollTo({ top: 0 });
    document.getElementById('view-heading')?.focus({ preventScroll: true });
  }, [view]);

  useEffect(() => {
    const name = toText(results?.filename);
    document.title = view === 'done' && name ? `${name} · IntelliLecture` : 'IntelliLecture · Lecture audio to study notes';
  }, [view, results]);

  const handleReset = useCallback(() => {
    runRef.current += 1;
    setJobIdInUrl(null);
    setJobId(null);
    setResults(null);
    setError(null);
    setUploadError('');
    setUploadPercent(0);
    setView('upload');
  }, []);

  const handleUpload = useCallback(async (file) => {
    const run = ++runRef.current;
    setUploadError('');
    setUploadPercent(0);
    setView('uploading');
    try {
      const data = await uploadAudio(file, {
        onProgress: (pct) => {
          if (run === runRef.current) setUploadPercent(pct);
        },
      });
      if (run !== runRef.current) return;
      setJobIdInUrl(data.job_id);
      setJobId(data.job_id);
      setView('processing');
    } catch (err) {
      if (run !== runRef.current) return;
      setUploadError(err?.message || 'Upload failed. Please try again.');
      setView('upload');
    }
  }, []);

  const loadResults = useCallback(async (id) => {
    const run = runRef.current;
    setView('loading');
    for (let attempt = 1; attempt <= RESULT_ATTEMPTS; attempt += 1) {
      try {
        const data = await getResults(id);
        if (run !== runRef.current) return;
        if (!data || typeof data !== 'object') throw new Error('Results were empty.');
        setResults(data);
        setView('done');
        return;
      } catch (err) {
        if (run !== runRef.current) return;
        if (err?.status === 404 || attempt === RESULT_ATTEMPTS) {
          setError({
            title: 'Could not load results',
            message: err?.message || 'The results could not be loaded.',
            retryable: err?.status !== 404,
          });
          setView('error');
          return;
        }
        await sleep(1500 * attempt);
      }
    }
  }, []);

  const handleProcessingError = useCallback((message, { retryable = false } = {}) => {
    setError({ title: 'Processing failed', message, retryable });
    setView('error');
  }, []);

  const handleRetry = useCallback(() => {
    setError(null);
    setView(jobId ? 'processing' : 'upload');
  }, [jobId]);

  const busy = view === 'uploading' || view === 'processing' || view === 'loading';

  return (
    <div className="app-container">
      <a className="skip-link" href="#main">Skip to content</a>

      <header className="app-nav">
        <div className="nav-brand">
          <div className="nav-logo" aria-hidden="true">IL</div>
          <div>
            <div className="nav-title">IntelliLecture</div>
            <div className="nav-subtitle">Lecture audio to study notes</div>
          </div>
        </div>
        {view !== 'upload' && (
          <button type="button" className="nav-button" onClick={handleReset} aria-label="New upload">
            <Plus size={15} aria-hidden="true" />
            <span>New upload</span>
          </button>
        )}
      </header>
      <div className="accent-strip" aria-hidden="true" />

      <main id="main" className={`app-main ${view === 'done' ? 'app-main--wide' : ''}`}>
        <ErrorBoundary key={view} onReset={handleReset}>
          {view === 'upload' && (
            <UploadView config={config} serverError={uploadError} onSubmit={handleUpload} />
          )}

          {busy && (
            <ProcessingView
              phase={view}
              jobId={jobId}
              uploadPercent={uploadPercent}
              onDone={() => loadResults(jobId)}
              onError={handleProcessingError}
            />
          )}

          {view === 'error' && (
            <ErrorView
              title={error?.title}
              message={error?.message}
              onReset={handleReset}
              onRetry={error?.retryable ? handleRetry : undefined}
            />
          )}

          {view === 'done' && results && (
            <Dashboard results={results} jobId={jobId} onReset={handleReset} />
          )}
        </ErrorBoundary>
      </main>

      <Footer />
    </div>
  );
}

export default App;
