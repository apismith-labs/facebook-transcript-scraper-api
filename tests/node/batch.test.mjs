import assert from 'node:assert/strict';
import { execFileSync, spawnSync } from 'node:child_process';
import { mkdtempSync, writeFileSync, readdirSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { test, runTests, FakeTransport, fixtureItems } from './harness.mjs';
import {
  estimateRows,
  parseRows,
  runBatch,
  splitCsvLine,
} from '../../examples/nodejs/batch-csv.mjs';
import { APPROVED_BUILD_ID, ApiError } from '../../examples/nodejs/reliable-actor.mjs';

const ITEMS = fixtureItems('transcript-success.synthetic.json');

function writeCsv(text) {
  const dir = mkdtempSync(join(tmpdir(), 'fb-csv-'));
  const path = join(dir, 'input.csv');
  writeFileSync(path, text, 'utf8');
  return path;
}

function successTransport() {
  return new FakeTransport([
    { data: { id: 'run-x', defaultDatasetId: 'ds-x', buildNumber: '0.0.18', buildId: APPROVED_BUILD_ID } },
    { data: { id: 'run-x', status: 'SUCCEEDED', defaultDatasetId: 'ds-x' } },
    ITEMS,
  ]);
}

test('CSV line splitting handles quotes and commas', () => {
  assert.deepEqual(splitCsvLine('a,b,c'), ['a', 'b', 'c']);
  assert.deepEqual(splitCsvLine('"a,1",b'), ['a,1', 'b']);
  assert.deepEqual(splitCsvLine('"he said ""hi""",b'), ['he said "hi"', 'b']);
});

test('rows keep line numbers, canonical URLs and optional durations', () => {
  const path = writeCsv(
    'videoUrl,durationSeconds\n' +
      'https://www.facebook.com/watch/?v=101,600\n' +
      '\n' +
      'https://www.facebook.com/reel/202/?mibextid=x,\n',
  );
  const rows = parseRows(path);
  assert.deepEqual(rows.map((row) => row.rowId), ['2', '4']);
  assert.equal(rows[0].canonicalUrl, 'https://www.facebook.com/watch/?v=101');
  assert.equal(rows[0].durationSeconds, 600);
  assert.equal(rows[1].form, 'reel');
  assert.equal(rows[1].durationSeconds, null);
});

test('duplicate URLs remain separate rows', () => {
  const path = writeCsv(
    'videoUrl\nhttps://www.facebook.com/reel/303/\nhttps://www.facebook.com/reel/303/\n',
  );
  const rows = parseRows(path);
  assert.equal(rows.length, 2);
  assert.notEqual(rows[0].rowId, rows[1].rowId);
});

test('url header and BOM are accepted', () => {
  const path = writeCsv('\uFEFFurl\nhttps://www.facebook.com/videos/404/\n');
  assert.equal(parseRows(path)[0].canonicalUrl, 'https://www.facebook.com/videos/404/');
});

test('invalid rows fail before any run', () => {
  const path = writeCsv('videoUrl\nhttps://www.instagram.com/reel/abc/\n');
  assert.throws(() => parseRows(path), /CSV line 2/);
});

test('missing column and bad durations are rejected', () => {
  assert.throws(() => parseRows(writeCsv('links\nhttps://www.facebook.com/reel/1/\n')), /videoUrl/);
  assert.throws(() => parseRows(writeCsv('videoUrl,durationSeconds\nhttps://www.facebook.com/reel/1/,abc\n')));
});

test('estimate sums per-row durations with a one-minute floor', () => {
  const estimate = estimateRows(
    [
      { rowId: '2', durationSeconds: 600 },
      { rowId: '3', durationSeconds: null },
    ],
    'FREE',
  );
  assert.equal(estimate.billedMinutes, 11);
  assert.ok(Math.abs(estimate.totalUsd - (0.002 + 0.0495)) < 1e-9);
  assert.equal(estimate.lowerBound, true);
  assert.throws(() => estimateRows([], 'ENTERPRISE'));
});

test('each row is one run and results keep input order', async () => {
  const rows = [
    { rowId: '2', url: 'https://www.facebook.com/watch/?v=701', canonicalUrl: 'https://www.facebook.com/watch/?v=701', form: 'watch', durationSeconds: 30 },
    { rowId: '3', url: 'https://www.facebook.com/reel/702/', canonicalUrl: 'https://www.facebook.com/reel/702/', form: 'reel', durationSeconds: 30 },
  ];
  const results = await runBatch(rows, {
    token: 'test-token',
    maxConcurrency: 2,
    journal: { append() {} },
    transportFactory: successTransport,
  });
  assert.deepEqual(results.map((row) => row.rowId), ['2', '3']);
  assert.ok(results.every((row) => row.status === 'success' && row.text));
});

test('one failed row does not stop the others', async () => {
  const rows = [
    { rowId: '2', url: 'https://www.facebook.com/watch/?v=801', canonicalUrl: 'https://www.facebook.com/watch/?v=801', form: 'watch', durationSeconds: 30 },
    { rowId: '3', url: 'https://www.facebook.com/reel/802/', canonicalUrl: 'https://www.facebook.com/reel/802/', form: 'reel', durationSeconds: 30 },
  ];
  let index = 0;
  const results = await runBatch(rows, {
    token: 'test-token',
    maxConcurrency: 1,
    journal: { append() {} },
    transportFactory: () => {
      index += 1;
      return index === 1 ? new FakeTransport([new ApiError('Apify HTTP 400', { status: 400 })]) : successTransport();
    },
  });
  assert.equal(results[0].status, 'transport_error');
  assert.equal(results[1].status, 'success');
});

test('CLI plan mode creates no Run and no file', () => {
  const path = writeCsv('videoUrl\nhttps://www.facebook.com/watch/?v=901\n');
  const dir = dirname(path);
  const cli = resolve(dirname(fileURLToPath(import.meta.url)), '../../examples/nodejs/batch-csv.mjs');
  const output = execFileSync(process.execPath, [cli, path], {
    encoding: 'utf8',
    env: { ...process.env, APIFY_TOKEN: '' },
  });
  assert.match(output, /Plan only/);
  assert.deepEqual(readdirSync(dir), ['input.csv']);
});

test('CLI execute without a token exits 2 and writes nothing', () => {
  const path = writeCsv('videoUrl\nhttps://www.facebook.com/watch/?v=902\n');
  const dir = dirname(path);
  const cli = resolve(dirname(fileURLToPath(import.meta.url)), '../../examples/nodejs/batch-csv.mjs');
  const result = spawnSync(process.execPath, [cli, path, '--execute'], {
    encoding: 'utf8',
    env: { ...process.env, APIFY_TOKEN: '' },
  });
  assert.equal(result.status, 2);
  assert.deepEqual(readdirSync(dir), ['input.csv']);
});

await runTests();
