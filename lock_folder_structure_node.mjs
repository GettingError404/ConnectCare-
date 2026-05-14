import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';

const repoRoot = path.resolve(path.dirname(new URL(import.meta.url).pathname), '.');
const lockFile = path.join(repoRoot, 'FOLDER_STRUCTURE.lock.json');

function fail(msg) {
  console.error(`[folder-structure-lock] ERROR: ${msg}`);
  process.exit(1);
}

if (!fs.existsSync(lockFile)) fail(`Missing lock file: ${lockFile}`);

const lock = JSON.parse(fs.readFileSync(lockFile, 'utf8'));
const allowed = new Set(lock.allowedTopLevelFolders ?? []);
if (allowed.size === 0) fail('Lock file contains no allowedTopLevelFolders');

const present = new Set(
  fs.readdirSync(repoRoot, { withFileTypes: true })
    .filter(d => d.isDirectory() && d.name !== '.git')
    .map(d => d.name)
);

const missing = [...allowed].filter(x => !present.has(x)).sort();
const extra = [...present].filter(x => !allowed.has(x)).sort();

if (missing.length || extra.length) {
  if (missing.length) {
    console.error('[folder-structure-lock] Missing top-level folders:');
    for (const m of missing) console.error(`  - ${m}`);
  }
  if (extra.length) {
    console.error('[folder-structure-lock] Unexpected extra top-level folders:');
    for (const e of extra) console.error(`  - ${e}`);
  }
  fail('Folder structure does not match the lock contract');
}

console.log('[folder-structure-lock] OK: Top-level folder structure matches the lock contract');

