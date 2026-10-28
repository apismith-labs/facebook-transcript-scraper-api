import assert from 'node:assert/strict';
import { mkdtempSync, readFileSync, statSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { test, runTests, FakeTransport, fixtureItems } from './harness.mjs';
import {
  APPROVED_BUILD_ID,
  APPROVED_BUILD_NUMBER,
  ApiError,
  RunJournal,
  classifyItems,
  executeInput,
  normalizeSegments,
  sanitize,
  summarize,
  validateBuild,
  validateRunChargeCap,
} from '../../examples/nodejs/reliable-actor.mjs';

const URL = 'https://www.facebook.com/watch/?v=1000000000000001';

test('build must be explicit and pinned', () => {
  assert.equal(validateBuild('0.0.18', { required: true }), '0.0.18');
  for (const bad of ['latest', '0.0.17', 'v0.0.18']) {
    assert.throws(() => validateBuild(bad, { required: true }));
  }
});

test('charge cap validation', () => {
  assert.equal(validateRunChargeCap('0.10'), 0.1);
  for (const bad of ['0', '-1', 'abc', 'NaN', 'Infinity']) {
    assert.throws(() => validateRunChargeCap(bad));
  }
  assert.throws(() => validateRunChargeCap(null, { required: true }));
});

test('classification precedence', () => {
  assert.equal(classifyItems([])[0], 'empty');
  assert.equal(classifyItems([{ text: 'x', errMsg: 'boom' }])[0], 'actor_error');
  assert.equal(classifyItems([{ text: 'hello', errMsg: '' }])[0], 'success');
  assert.equal(classifyItems([{ text: null, errMsg: '' }])[0], 'no_transcript');
  assert.equal(classifyItems([{ text: 7, errMsg: '' }])[0], 'unknown');
  assert.equal(classifyItems('not a list')[0], 'unknown');
});

test('segments normalization filters invalid entries', () => {
  const value = fixtureItems('segments-invalid.synthetic.json')[0].segments;
  assert.deepEqual(normalizeSegments(value), [
    { start: 0, end: 1.2, text: 'valid one' },
    { start: 4, end: 5, text: 'valid two' },
  ]);
  assert.deepEqual(normalizeSegments(null), []);
});

test('sanitize removes credentials recursively', () => {
  const cleaned = sanitize({
    APIFY_TOKEN: 'secret',
    nested: [{ authorization: 'Bearer abc', text: 'Bearer abcdef' }],
  });
  assert.equal(cleaned.APIFY_TOKEN, undefined);
  assert.equal(cleaned.nested[0].authorization, undefined);
  assert.equal(cleaned.nested[0].text, 'Bearer [REDACTED]');
});

test('summarize counts every status', () => {
  const counts = summarize([{ status: 'success' }, { status: 'actor_error' }, { status: 'weird' }]);
  assert.equal(counts.success, 1);
  assert.equal(counts.actor_error, 1);
  assert.equal(counts.unknown, 1);
  assert.equal(counts.processed, 3);
  assert.equal(counts.failed, 2);
});

test('journal appends, reads back and uses owner-only permissions', () => {
  const dir = mkdtempSync(join(tmpdir(), 'fb-journal-'));
  const path = join(dir, 'journal.jsonl');
  const journal = new RunJournal(path);
  journal.append({ runId: 'run-1', stage: 'creating' });
  journal.append({ runId: 'run-1', stage: 'complete' });
  assert.equal(journal.latest('run-1').stage, 'complete');
  assert.equal(journal.latest('run-2'), null);
  assert.equal(statSync(path).mode & 0o777, 0o600);
});

test('corrupt journal refuses to append', () => {
  const dir = mkdtempSync(join(tmpdir(), 'fb-journal-'));
  const path = join(dir, 'journal.jsonl');
  writeFileSync(path, '{"ok":true}\nnot json\n');
  assert.throws(() => new RunJournal(path).append({ runId: 'run-1' }));
  assert.match(readFileSync(path, 'utf8'), /not json/);
});

test('transient GET failures are retried on the same Run', async () => {
  const transport = new FakeTransport([
    { data: { id: 'run-1', defaultDatasetId: 'ds-1', buildNumber: '0.0.18', buildId: APPROVED_BUILD_ID } },
    new ApiError('Apify HTTP 503', { status: 503 }),
    new ApiError('Apify HTTP 503', { status: 503 }),
    { data: { id: 'run-1', status: 'SUCCEEDED', defaultDatasetId: 'ds-1', buildNumber: '0.0.18', buildId: APPROVED_BUILD_ID } },
    fixtureItems('transcript-success.synthetic.json'),
  ]);
  const outcome = await executeInput({
    transport,
    actorId: 'apple_yang/facebook-transcript-scraper-api',
    runInput: { videoUrl: URL },
    sourceUrl: URL,
    journal: { append() {} },
    build: '0.0.18',
    requireBuild: true,
    datasetLimit: 100,
    sleep: async () => {},
  });
  assert.equal(outcome.status, 'success');
  assert.equal(transport.postCount, 1);
});

test('exhausted retries return transport_error with the run id', async () => {
  const transport = new FakeTransport([
    { data: { id: 'run-1', defaultDatasetId: 'ds-1', buildNumber: '0.0.18', buildId: APPROVED_BUILD_ID } },
    new ApiError('Apify HTTP 503', { status: 503 }),
    new ApiError('Apify HTTP 503', { status: 503 }),
    new ApiError('Apify HTTP 503', { status: 503 }),
    new ApiError('Apify HTTP 503', { status: 503 }),
  ]);
  const outcome = await executeInput({
    transport,
    actorId: 'apple_yang/facebook-transcript-scraper-api',
    runInput: { videoUrl: URL },
    sourceUrl: URL,
    journal: { append() {} },
    build: '0.0.18',
    requireBuild: true,
    sleep: async () => {},
  });
  assert.equal(outcome.status, 'transport_error');
  assert.equal(outcome.runId, 'run-1');
  assert.equal(transport.postCount, 1);
});

test('missing run id in the create response is creation_unknown', async () => {
  const transport = new FakeTransport([{ data: { defaultDatasetId: 'ds-1' } }]);
  const outcome = await executeInput({
    transport,
    actorId: 'apple_yang/facebook-transcript-scraper-api',
    runInput: { videoUrl: URL },
    sourceUrl: URL,
    journal: { append() {} },
    build: '0.0.18',
    requireBuild: true,
  });
  assert.equal(outcome.status, 'creation_unknown');
  assert.equal(transport.postCount, 1);
});

test('default build pins match the audited build', () => {
  assert.equal(APPROVED_BUILD_NUMBER, '0.0.18');
  assert.equal(APPROVED_BUILD_ID, 'fZIlpYENof2jYqIJc');
});

await runTests();
