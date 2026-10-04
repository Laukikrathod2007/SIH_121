# NWIS Evidence Server

A minimal Node/Express service that serves the bundled sample DDR
(Daily Drilling Report) PDFs so the frontend's EvidenceViewer citation
links open a real document. Standalone process, not part of `frontend/`
or any of the `modules/` FastAPI services — must be started separately.

This service still runs as its own process in this pass; retiring it into
the unified backend (per the planned service-consolidation pass) is
separate, later work and has not happened here.

## Run

```bash
cd evidence-server
npm install
npm start          # listens on http://localhost:4100 by default
```

Override the port with `PORT=<n> npm start`. The default (4100, not
Express's more common 3000/8080) matches `frontend`'s
`VITE_EVIDENCE_SERVER` fallback and the rest of this repo's documentation
— no override needed for the normal local-dev setup.

## Endpoints

### `GET /evidence?name=<filename.pdf>`
Streams a PDF from `pdfs/` with `Content-Type: application/pdf`.
- Missing/invalid `name` (absent, not a string, or containing `..`, `/`,
  `\`) → `400 Invalid document name`.
- A resolved path that would escape `pdfs/` (defense in depth, on top of
  the substring check above) → `400 Invalid document name`.
- File not found → `404 Document not found.` (the response body does
  **not** list any real filenames from the PDF directory — fixed in Pass 2,
  which previously leaked the first 5 real filenames here).

### `GET /health`
```json
{ "status": "healthy", "pdf_dir_reachable": true, "pdf_count": 42 }
```
`status` is `"degraded"` and `pdf_count` is `null` if the PDF directory
can't be read. No heavy work is done on every call — just a directory read.

### `GET /`
Human-readable landing page with a PDF count.

## Security notes

- **No authentication.** This serves a fixed set of bundled sample
  documents from a local directory — there is nothing per-user or secret
  behind this endpoint. If that assumption changes (e.g. real/sensitive
  documents are ever added to `pdfs/`), this needs gating before that
  happens.
- **CORS is wide open** (`Access-Control-Allow-Origin: *`) — acceptable
  given the above; revisit together with the auth assumption if it changes.
- **Path traversal**: two layers — a substring blocklist (`..`, `/`, `\`)
  on the raw filename, plus a `path.resolve()` + prefix check verifying
  the resolved path still falls inside `pdfs/` before any filesystem
  access. Neither check alone is assumed sufficient; both run on every
  request.
- Unexpected filesystem errors are caught by a terminal Express error
  handler and returned as clean JSON (`{"error": "internal_server_error"}`)
  rather than Express's default error page.

## Tests

```bash
npm test
```

Runs `test/smoke-test.js` — a small, dependency-free script (Node's
built-in `child_process` + global `fetch`, no Jest/Supertest added) that
starts the server on an ephemeral port and verifies: `/health` is
reachable and reports a real PDF count; a missing file returns `404` with
no directory-listing leak; several path-traversal payloads are rejected
with `400`; and a real, valid filename still streams back correctly as
`application/pdf`.
