/**
 * Minimal PDF-evidence server. Serves the bundled sample DDR PDFs so the
 * EvidenceViewer's citation links open a real document.
 *
 * Run: node server/index.js   (defaults to http://localhost:4000)
 */
const express = require('express');
const path = require('path');
const fs = require('fs');

const app = express();
const PORT = process.env.PORT || 4000;
const PDF_DIR = path.join(__dirname, 'pdfs');

app.use((req, res, next) => {
  res.header('Access-Control-Allow-Origin', '*');
  next();
});

app.get('/evidence', (req, res) => {
  const name = req.query.name;
  if (!name || typeof name !== 'string' || name.includes('..') || name.includes('/') || name.includes('\\')) {
    return res.status(400).send('Invalid document name');
  }
  const filePath = path.join(PDF_DIR, name);
  if (!fs.existsSync(filePath)) {
    return res.status(404).send(`Document "${name}" not found. Available: ${fs.readdirSync(PDF_DIR).slice(0, 5).join(', ')}...`);
  }
  res.setHeader('Content-Type', 'application/pdf');
  res.setHeader('Content-Disposition', `inline; filename="${name}"`);
  fs.createReadStream(filePath).pipe(res);
});

app.get('/', (req, res) => {
  const files = fs.readdirSync(PDF_DIR);
  res.send(`<h1>NWIS Evidence Server</h1><p>${files.length} PDFs available.</p><p>GET /evidence?name=&lt;filename.pdf&gt;</p>`);
});

app.listen(PORT, () => {
  console.log(`Evidence server running at http://localhost:${PORT}`);
  console.log(`Serving ${fs.readdirSync(PDF_DIR).length} PDFs from ${PDF_DIR}`);
});
