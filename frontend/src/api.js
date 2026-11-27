// Thin client for the IntelliLecture backend API.
// VITE_API_URL lets the frontend be hosted separately from the backend;
// when unset, requests go to /api on the same origin (proxied by Vite in dev).
export const API_URL = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '') + '/api';

export class ApiError extends Error {
  constructor(message, status = 0) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

const FALLBACK_MESSAGES = {
  400: 'The request was not accepted by the server.',
  404: 'The requested item could not be found.',
  413: 'The file is too large for the server to accept.',
  415: 'This file type is not supported.',
  429: 'Too many requests right now. Please wait a moment and try again.',
  500: 'The server ran into a problem. Please try again.',
  502: 'The server is temporarily unavailable.',
  503: 'The server is temporarily unavailable.',
};

const NETWORK_MESSAGE = 'Could not reach the server. Check your connection and try again.';

function detailToMessage(detail) {
  if (!detail) return '';
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d) => (d && typeof d === 'object' ? d.msg || d.message || '' : String(d)))
      .filter(Boolean)
      .join('; ');
  }
  if (typeof detail === 'object') return detail.message || detail.msg || '';
  return String(detail);
}

function messageFor(status, bodyText) {
  let parsed = null;
  try {
    parsed = bodyText ? JSON.parse(bodyText) : null;
  } catch {
    parsed = null;
  }
  return (
    detailToMessage(parsed?.detail) ||
    FALLBACK_MESSAGES[status] ||
    `Request failed (HTTP ${status}).`
  );
}

async function getJson(path, { signal } = {}) {
  let res;
  try {
    res = await fetch(`${API_URL}${path}`, { signal, headers: { Accept: 'application/json' } });
  } catch (err) {
    if (err?.name === 'AbortError') throw err;
    throw new ApiError(NETWORK_MESSAGE, 0);
  }
  const text = await res.text();
  if (!res.ok) throw new ApiError(messageFor(res.status, text), res.status);
  try {
    return text ? JSON.parse(text) : {};
  } catch {
    throw new ApiError('The server sent an unexpected response.', res.status);
  }
}

export const getConfig = (opts) => getJson('/config', opts);

export const getStatus = (jobId, opts) =>
  getJson(`/status/${encodeURIComponent(jobId)}`, opts);

export const getResults = (jobId, opts) =>
  getJson(`/results/${encodeURIComponent(jobId)}`, opts);

export const exportUrl = (jobId, format) =>
  `${API_URL}/export/${encodeURIComponent(jobId)}?format=${encodeURIComponent(format)}`;

/**
 * Upload an audio file. Uses XMLHttpRequest so upload progress can be reported.
 * Resolves with {job_id, status}; rejects with ApiError carrying the server's detail.
 */
export function uploadAudio(file, { onProgress } = {}) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', `${API_URL}/upload`);
    xhr.setRequestHeader('Accept', 'application/json');

    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress(Math.min(100, Math.round((e.loaded / e.total) * 100)));
      }
    };

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const data = JSON.parse(xhr.responseText);
          if (!data || typeof data.job_id !== 'string' || !data.job_id) throw new Error('missing job id');
          resolve(data);
        } catch {
          reject(new ApiError('The server sent an unexpected response.', xhr.status));
        }
      } else {
        reject(new ApiError(messageFor(xhr.status, xhr.responseText), xhr.status));
      }
    };
    xhr.onerror = () => reject(new ApiError(NETWORK_MESSAGE, 0));
    xhr.onabort = () => reject(new ApiError('Upload cancelled.', 0));

    const form = new FormData();
    form.append('audio_file', file);
    xhr.send(form);
  });
}
