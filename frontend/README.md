# IntelliLecture — Frontend

React + Vite single-page app for IntelliLecture: upload a lecture recording and browse the
generated transcript, summary, keywords and topics, quiz, flashcards and quality metrics, with
PDF / Markdown export.

## Development

```bash
npm install
npm run dev:frontend   # Vite dev server on http://localhost:5173
```

In development, requests to `/api` are proxied to the backend at `http://127.0.0.1:8000`
(see `vite.config.js`).

To start the backend and frontend together (requires the Python virtual environment to be
activated in the same shell):

```bash
npm run dev
```

## Build

```bash
npm run lint
npm run build     # outputs static files to dist/
npm run preview   # serve the production build locally
```

## Configuration

| Variable       | Default        | Purpose                                                                 |
| -------------- | -------------- | ----------------------------------------------------------------------- |
| `VITE_API_URL` | _(empty)_      | Backend origin when the frontend is hosted separately, e.g. `https://api.example.com`. `/api` is appended automatically. Leave empty to use same-origin `/api`. |

Set it at build time, e.g. `VITE_API_URL=https://api.example.com npm run build`, or in a
`.env.local` file.

## Structure

```
src/
  api.js                 API client (config, upload, status, results, export URLs)
  utils.js               formatting + URL (?job=) helpers
  hooks/useJobPolling.js status polling with retry on network blips
  components/            upload, processing, error, dashboard views
  components/tabs/       transcript, summary, keywords, quiz, flashcards, metrics
```

A job id is kept in the URL (`?job=<id>`), so refreshing or sharing the page resumes the job
or reopens its results.
