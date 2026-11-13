/* Negative CLI cases run entirely in a temporary workbench; no browser is launched. */
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');

const root = fs.mkdtempSync(path.join(os.tmpdir(), 'journal-node-diagnostics-'));
const checkEdition = path.resolve(__dirname, '../assets/destination-reference/check-edition.cjs');
const checkEngine = path.join(__dirname, 'check_current_engine.cjs');
const workbench = path.join(root, 'workbench');
const modules = path.join(root, 'node_modules');
fs.mkdirSync(workbench);
fs.mkdirSync(modules);
const html = path.join(workbench, 'index.html');
fs.writeFileSync(html, '<!doctype html><title>QA fixture</title>');

function rejects(script, target, expressions, environment = {}) {
  const result = spawnSync(process.execPath, [script, target], {
    encoding: 'utf8',
    timeout: 10000,
    env: { ...process.env, JOURNAL_CHECK_MODULES: modules, ...environment }
  });
  assert.ifError(result.error);
  assert.notEqual(result.status, 0, 'Expected invalid input to fail');
  const output = result.stdout + result.stderr;
  for (const expression of expressions) assert.match(output, expression);
}

rejects(checkEdition, html, [/Expected a workbench directory/, /received a file/, /containing workbench directory/]);
rejects(checkEdition, path.join(root, 'missing'), [/Workbench directory does not exist/, /Usage:/]);
rejects(checkEdition, root, [/Missing index\.html/, /build\.py/]);
for (const name of ['jsdom', 'fake-indexeddb', 'css-tree']) {
  rejects(checkEdition, workbench, [new RegExp('DOM QA requires ' + name), /JOURNAL_CHECK_MODULES/, /npm install/, /Supplied directory:/]);
  const packageRoot = path.join(modules, name);
  fs.mkdirSync(packageRoot);
  fs.writeFileSync(path.join(packageRoot, 'index.js'), 'module.exports = {};');
}

// The mismatch must fail before launch; a deliberately unusable browser module enforces that.
const playwright = path.join(modules, 'playwright-core');
fs.mkdirSync(playwright);
fs.writeFileSync(path.join(playwright, 'index.js'), 'module.exports = { chromium: { launch() { throw new Error("Browser must not launch for an invalid hash"); } } };');
fs.writeFileSync(path.join(workbench, 'build-manifest.json'), JSON.stringify({ artifact: 'index.html', sha256: 'incorrect' }));
rejects(checkEngine, workbench, [/Standalone HTML does not match build-manifest\.json/, /python -X utf8 build\.py/, /rerun this check/], { JOURNAL_CHROME: process.execPath });
console.log('PASS Node diagnostics: HTML/nonexistent/empty directory, all three missing DOM dependencies, stale artifact hash.');
