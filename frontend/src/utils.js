// Small, defensive helpers shared across components.

export const asArray = (v) => (Array.isArray(v) ? v : []);

export const isNum = (v) => typeof v === 'number' && Number.isFinite(v);

/** Coerce any value into display text without ever returning an object. */
export function toText(v) {
  if (v == null) return '';
  if (typeof v === 'string') return v;
  if (typeof v === 'number' || typeof v === 'boolean') return String(v);
  if (typeof v === 'object' && !Array.isArray(v)) {
    for (const key of ['text', 'keyword', 'term', 'name', 'title', 'label', 'value']) {
      if (typeof v[key] === 'string') return v[key];
    }
  }
  return '';
}

function pad(n) {
  return String(n).padStart(2, '0');
}

/** Seconds -> mm:ss, or h:mm:ss when the value (or forceHours) needs it. */
export function formatTimestamp(sec, forceHours = false) {
  if (!isNum(sec) || sec < 0) return '';
  const total = Math.floor(sec);
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  if (h > 0 || forceHours) return `${h}:${pad(m)}:${pad(s)}`;
  return `${pad(m)}:${pad(s)}`;
}

/** Seconds -> "1h 02m", "12m 30s" or "45s". */
export function formatDuration(sec) {
  if (!isNum(sec) || sec < 0) return '';
  const total = Math.round(sec);
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  if (h > 0) return `${h}h ${pad(m)}m`;
  if (m > 0) return `${m}m ${pad(s)}s`;
  return `${s}s`;
}

export function formatBytes(bytes) {
  if (!isNum(bytes) || bytes < 0) return '';
  if (bytes < 1024) return `${bytes} B`;
  const units = ['KB', 'MB', 'GB'];
  let value = bytes / 1024;
  let i = 0;
  while (value >= 1024 && i < units.length - 1) {
    value /= 1024;
    i += 1;
  }
  return `${value.toFixed(value >= 10 ? 0 : 1)} ${units[i]}`;
}

export function formatDate(iso) {
  if (typeof iso !== 'string' || !iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  return d.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
}

export function getExtension(name) {
  if (typeof name !== 'string') return '';
  const i = name.lastIndexOf('.');
  return i > 0 ? name.slice(i).toLowerCase() : '';
}

const PROVIDER_LABELS = {
  groq: 'Groq (cloud)',
  local: 'Local models',
  'openai-compatible': 'OpenAI-compatible API',
};

export const providerLabel = (p) => PROVIDER_LABELS[p] || toText(p);

export function escapeRegExp(s) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/* ── URL state (?job=<id>) ─────────────────────────── */

export function getJobIdFromUrl() {
  try {
    return new URLSearchParams(window.location.search).get('job') || null;
  } catch {
    return null;
  }
}

export function setJobIdInUrl(jobId) {
  try {
    const url = new URL(window.location.href);
    if (jobId) url.searchParams.set('job', jobId);
    else url.searchParams.delete('job');
    window.history.replaceState(window.history.state, '', url.toString());
  } catch {
    // History API unavailable; the app still works without URL persistence.
  }
}
