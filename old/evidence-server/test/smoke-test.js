/**
 * Lightweight, dependency-free smoke test for evidence-server's Pass 2
 * hardening. No test framework added -- just Node's built-in child_process
 * and global fetch (Node 18+), run via `npm test`.
 *
 * Starts the server as a child process on an ephemeral-ish port, exercises
 * it over real HTTP, then kills it. Exits non-zero on any assertion failure
 * so `npm test` fails CI/manual runs correctly.
 */
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const PORT = 4199; // unlikely to collide with a real running instance on 4100
const BASE_URL = `http://localhost:${PORT}`;
const PDF_DIR = path.join(__dirname, '..', 'pdfs');

let failures = 0;

function assert(condition, message) {
  if (!condition) {
    failures += 1;
    console.error(`FAIL: ${message}`);
  } else {
    console.log(`PASS: ${message}`);
  }
}

async function waitForServer(maxAttempts = 30) {
  for (let i = 0; i < maxAttempts; i++) {
    try {
      const res = await fetch(`${BASE_URL}/health`);
      if (res.ok) return true;
    } catch (err) {
      // not up yet
    }
    await new Promise((resolve) => setTimeout(resolve, 200));
  }
  return false;
}

async function main() {
  const serverProcess = spawn(process.execPath, [path.join(__dirname, '..', 'index.js')], {
    env: { ...process.env, PORT: String(PORT) },
    stdio: 'pipe',
  });

  serverProcess.stderr.on('data', (chunk) => {
    // surfaced only on failure investigation; not asserted on
    process.stderr.write(`[server stderr] ${chunk}`);
  });

  try {
    const up = await waitForServer();
    assert(up, 'server started and /health became reachable');
    if (!up) {
      throw new Error('server never came up; aborting remaining checks');
    }

    // --- /health ---
    const healthRes = await fetch(`${BASE_URL}/health`);
    const healthBody = await healthRes.json();
    assert(healthRes.status === 200, '/health returns 200');
    assert(healthBody.status === 'healthy', '/health reports status: healthy');
    assert(typeof healthBody.pdf_count === 'number' && healthBody.pdf_count > 0, '/health reports a positive pdf_count');

    // --- missing file: no directory-listing leak ---
    const realFilenames = fs.readdirSync(PDF_DIR);
    assert(realFilenames.length > 0, 'PDF_DIR has real files to test against');
    const missingRes = await fetch(`${BASE_URL}/evidence?name=does-not-exist-xyz.pdf`);
    const missingBody = await missingRes.text();
    assert(missingRes.status === 404, 'missing file returns 404');
    const leaksAFilename = realFilenames.some((f) => missingBody.includes(f));
    assert(!leaksAFilename, '404 body does not leak any real filename from PDF_DIR');

    // --- path traversal attempts rejected ---
    const traversalAttempts = [
      '../package.json',
      '..%2Fpackage.json',
      '..\\package.json',
      '....//package.json',
    ];
    for (const attempt of traversalAttempts) {
      const res = await fetch(`${BASE_URL}/evidence?name=${attempt}`);
      assert(res.status === 400, `traversal attempt "${attempt}" rejected with 400 (got ${res.status})`);
    }

    // --- valid file still served correctly (regression guard) ---
    const validName = realFilenames[0];
    const validRes = await fetch(`${BASE_URL}/evidence?name=${encodeURIComponent(validName)}`);
    assert(validRes.status === 200, `valid filename "${validName}" returns 200`);
    assert(
      validRes.headers.get('content-type') === 'application/pdf',
      'valid file response has Content-Type: application/pdf'
    );
  } finally {
    serverProcess.kill();
  }

  if (failures > 0) {
    console.error(`\n${failures} assertion(s) failed.`);
    process.exit(1);
  } else {
    console.log('\nAll evidence-server smoke tests passed.');
    process.exit(0);
  }
}

main().catch((err) => {
  console.error('Smoke test crashed:', err);
  process.exit(1);
});
