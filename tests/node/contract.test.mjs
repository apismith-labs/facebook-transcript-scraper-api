import assert from 'node:assert/strict';
import { readFileSync, readdirSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { test, runTests, FIXTURE_DIR, fixtureItems } from './harness.mjs';
import { classifyItems } from '../../examples/nodejs/reliable-actor.mjs';
import { DATASET_ITEM_USD, TIER_PRICES_USD_PER_MINUTE } from '../../examples/nodejs/cost.mjs';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
const CONTRACT = JSON.parse(
  readFileSync(resolve(ROOT, 'docs/audit/contracts/facebook-transcript-scraper-api-0.0.18.json'), 'utf8'),
);

const EXPECTED = {
  'transcript-success.synthetic.json': 'success',
  'transcript-actor-error.synthetic.json': 'actor_error',
  'dataset-empty.synthetic.json': 'empty',
  'no-transcript-null.synthetic.json': 'no_transcript',
  'no-transcript-missing.synthetic.json': 'no_transcript',
  'unknown-text-type.synthetic.json': 'unknown',
  'extra-fields.synthetic.json': 'success',
  'segments-invalid.synthetic.json': 'success',
};

test('contract pins the same build as the clients', () => {
  assert.equal(CONTRACT.actor.buildNumber, '0.0.18');
  assert.equal(CONTRACT.actor.buildId, 'fZIlpYENof2jYqIJc');
});

test('the actor has exactly one input field', () => {
  assert.deepEqual(Object.keys(CONTRACT.input.fields), ['videoUrl']);
  assert.deepEqual(CONTRACT.input.required, ['videoUrl']);
  for (const absent of ['bulkUrls', 'usernames', 'sessionid']) {
    assert.ok(absent in CONTRACT.input.absentFields);
  }
});

test('fixture fields match the audited dataset schema', () => {
  const fields = Object.keys(CONTRACT.output.datasetFields).sort();
  const item = fixtureItems('transcript-success.synthetic.json')[0];
  assert.deepEqual(Object.keys(item).sort(), fields);
  assert.equal(fields.length, 17);
});

test('undocumented item fields are recorded', () => {
  assert.deepEqual(CONTRACT.output.documentedButNotInReadme.sort(), ['likesCount', 'shareCount']);
});

test('pricing snapshot matches the cost model', () => {
  assert.equal(CONTRACT.pricing.events['apify-default-dataset-item'].priceUsd, DATASET_ITEM_USD);
  const tiers = CONTRACT.pricing.events.speech2text.tieredPriceUsdPerMinute;
  assert.equal(tiers.FREE, TIER_PRICES_USD_PER_MINUTE.FREE);
  assert.equal(tiers.GOLD, TIER_PRICES_USD_PER_MINUTE.GOLD);
  assert.equal(CONTRACT.limits.freePlanVideoDurationMinutes, 5);
});

test('every fixture classifies as expected', () => {
  for (const [name, expected] of Object.entries(EXPECTED)) {
    assert.equal(classifyItems(fixtureItems(name))[0], expected, name);
  }
});

test('the fixture set is fully covered', () => {
  const onDisk = readdirSync(FIXTURE_DIR).filter((name) => name.endsWith('.synthetic.json')).sort();
  assert.deepEqual(onDisk, Object.keys(EXPECTED).sort());
});

await runTests();
