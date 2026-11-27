import { useEffect, useRef, useState } from 'react';
import { getStatus } from '../api';
import { toText } from '../utils';

/**
 * Polls /api/status/{jobId} with a setTimeout chain (no overlapping requests).
 * Transient network failures are retried; only `maxFailures` consecutive
 * failures surface as an error. Polling stops on unmount or when jobId changes.
 */
export default function useJobPolling(jobId, { onDone, onError, interval = 2500, maxFailures = 5 } = {}) {
  const [status, setStatus] = useState(null);
  const [retrying, setRetrying] = useState(false);

  // Keep the latest callbacks without restarting the polling loop.
  const handlers = useRef({ onDone, onError });
  useEffect(() => {
    handlers.current = { onDone, onError };
  });

  useEffect(() => {
    if (!jobId) return undefined;

    let cancelled = false;
    let timer = null;
    let failures = 0;
    const controller = new AbortController();

    async function tick() {
      try {
        const data = await getStatus(jobId, { signal: controller.signal });
        if (cancelled) return;
        failures = 0;
        setRetrying(false);
        setStatus(data && typeof data === 'object' ? data : null);
        if (data?.status === 'done') {
          handlers.current.onDone?.(data);
          return;
        }
        if (data?.status === 'error') {
          handlers.current.onError?.(
            toText(data.error) || 'Processing failed on the server.',
            { retryable: false },
          );
          return;
        }
      } catch (err) {
        if (cancelled || err?.name === 'AbortError') return;
        if (err?.status === 404) {
          handlers.current.onError?.(
            'This job could not be found. It may have expired or the server was restarted.',
            { retryable: false },
          );
          return;
        }
        failures += 1;
        if (failures >= maxFailures) {
          handlers.current.onError?.(
            err?.message || 'Lost connection to the server while processing.',
            { retryable: true },
          );
          return;
        }
        setRetrying(true);
      }
      timer = setTimeout(tick, interval);
    }

    tick();

    return () => {
      cancelled = true;
      controller.abort();
      clearTimeout(timer);
    };
  }, [jobId, interval, maxFailures]);

  return { status, retrying };
}
