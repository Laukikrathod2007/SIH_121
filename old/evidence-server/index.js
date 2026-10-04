/**
 * Minimal PDF-evidence server. Serves the bundled sample DDR PDFs so the
 * EvidenceViewer's citation links open a real document.
 *
 * Run: node index.js   (defaults to http://localhost:4100 -- matches
 * frontend's VITE_EVIDENCE_SERVER fallback and AUDIT/ docs elsewhere in
 * this repo; override with PORT=<n> if you need a different port.)
 */
const express = require('express');
const path = require('path');
const fs = require('fs');

const app = express();
const PORT = process.env.PORT || 4100;
const PDF_DIR = path.join(__dirname, 'pdfs');
const PDF_DIR_RESOLVED = path.resolve(PDF_DIR);

app.use((req, res, next) => {
  res.header('Access-Control-Allow-Origin', '*');
  next();
});

app.get('/evidence', (req, res) => {
  const name = req.query.name;
  if (!name || typeof name !== 'string' || name.includes('..') || name.includes('/') || name.includes('\\')) {
    return res.status(400).send('Invalid document name');
  }
  const resolvedPath = path.resolve(path.join(PDF_DIR, name));
  // Defense in depth, on top of the substring blocklist above: verify the
  // resolved path still falls strictly inside PDF_DIR before touching the
  // filesystem with it. Mirrors modules/01_document_intelligence/api/
  // routes/results.py's canonicalization check -- should be unreachable
  // given the blocklist above, but never serve a file outside PDF_DIR.
  if (resolvedPath !== PDF_DIR_RESOLVED && !resolvedPath.startsWith(PDF_DIR_RESOLVED + path.sep)) {
    return res.status(400).send('Invalid document name');
  }
  if (!fs.existsSync(resolvedPath)) {
    // Pass 2 hardening: this used to embed the first 5 real filenames in
    // PDF_DIR in the error body ("Available: a.pdf, b.pdf, ..."), which
    // leaked directory contents to any caller requesting a nonexistent
    // name. Generic message now; real filenames are never disclosed here.
    return res.status(404).send('Document not found.');
  }
  res.setHeader('Content-Type', 'application/pdf');
  res.setHeader('Content-Disposition', `inline; filename="${name}"`);
  fs.createReadStream(resolvedPath).pipe(res);
});

// GET /health -- Pass 2 hardening: this service had no health endpoint at
// all. Lightweight by design: just confirms PDF_DIR is actually readable
// and reports how many PDFs are there, no heavy work on every call.
app.get('/health', (req, res) => {
  let pdfCount = null;
  let pdfDirReachable = false;
  try {
    pdfCount = fs.readdirSync(PDF_DIR).length;
    pdfDirReachable = true;
  } catch (err) {
    console.error(`Health check: PDF_DIR unreachable: ${err.message}`);
  }
  res.json({
    status: pdfDirReachable ? 'healthy' : 'degraded',
    pdf_dir_reachable: pdfDirReachable,
    pdf_count: pdfCount,
  });
});

app.get('/', (req, res) => {
  let files;
  try {
    files = fs.readdirSync(PDF_DIR);
  } catch (err) {
    console.error(`Root route: PDF_DIR unreachable: ${err.message}`);
    return res.status(503).send('Evidence server is degraded: PDF directory is unreachable.');
  }
  res.send(`<h1>NWIS Evidence Server</h1><p>${files.length} PDFs available.</p><p>GET /evidence?name=&lt;filename.pdf&gt;</p>`);
});

// Terminal error-handling middleware (4-arg signature) -- Pass 2 hardening:
// without this, an unexpected synchronous error inside a route handler
// (e.g. a filesystem error not already caught above) fell through to
// Express's default error page, whose verbosity depends on NODE_ENV (never
// set anywhere in this file). This guarantees a clean JSON response
// instead, with full detail logged server-side only.
app.use((err, req, res, next) => {
  console.error('Unhandled error:', err);
  res.status(500).json({ error: 'internal_server_error' });
});

app.listen(PORT, () => {
  console.log(`Evidence server running at http://localhost:${PORT}`);
  try {
    console.log(`Serving ${fs.readdirSync(PDF_DIR).length} PDFs from ${PDF_DIR}`);
  } catch (err) {
    console.error(`Startup warning: PDF_DIR unreachable: ${err.message}`);
  }
});
