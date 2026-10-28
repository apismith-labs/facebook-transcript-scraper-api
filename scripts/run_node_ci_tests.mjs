#!/usr/bin/env node
/** Run every tests/node/*.test.mjs file in a separate process and aggregate exit codes. */
import { spawnSync } from 'node:child_process';
import { readdirSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const TEST_DIR = resolve(HERE, '../tests/node');
const files = readdirSync(TEST_DIR)
  .filter((name) => name.endsWith('.test.mjs'))
  .sort();

let failed = 0;
for (const file of files) {
  console.log(`\n# ${file}`);
  const result = spawnSync(process.execPath, [resolve(TEST_DIR, file)], { stdio: 'inherit' });
  if (result.status !== 0) {
    failed += 1;
    console.error(`FAILED: ${file}`);
  }
}

console.log(`\n${files.length - failed}/${files.length} test files passed`);
process.exit(failed ? 1 : 0);
