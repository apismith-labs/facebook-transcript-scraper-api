import assert from 'node:assert/strict';
import { test, runTests, FakeTransport, fixtureItems } from './harness.mjs';
import {
  ConfigurationError,
  CreationUnknownError,
  ProtocolError,
  TransportError,
  getTranscript,
} from '../../examples/nodejs/client.mjs';
import { APPROVED_BUILD_ID, ApiError } from '../../examples/nodejs/reliable-actor.mjs';

const URL = 'https://www.facebook.com/watch/?v=1000000000000001';

function successTransport(items, { buildNumber = '0.0.18', buildId = APPROVED_BUILD_ID, polls = ['SUCCEEDED'] } = {}) {
  const responses = [
    { data: { id: 'run-synthetic', defaultDatasetId: 'dataset-synthetic', buildNumber, buildId } },
  ];
  for (const status of polls) {
    responses.push({ data: { id: 'run-synthetic', status, defaultDatasetId: 'dataset-synthetic' } });
  }
  responses.push(items);
  return new FakeTransport(responses);
}

test('success returns text, normalized segments and metadata', async () => {
  const transport = successTransport(fixtureItems('transcript-success.synthetic.json'));
  const result = await getTranscript(URL, { token: 'test-token', transport });

  assert.equal(result.status, 'success');
  assert.equal(result.succeeded, true);
  assert.equal(result.text, 'This is a synthetic transcript used only by offline tests.');
  assert.equal(result.segments.length, 2);
  assert.deepEqual(result.segments[0], { start: 0, end: 2.4, text: 'This is a synthetic transcript' });
  assert.equal(result.title, 'Synthetic video for offline tests');
  assert.equal(result.duration, 43.5);
  assert.equal(result.nickname, 'Synthetic Creator');
  assert.equal(result.runId, 'run-synthetic');
  assert.equal(result.datasetId, 'dataset-synthetic');
  assert.equal(result.urlForm, 'watch');
});

test('one pinned POST with canonical input and run options', async () => {
  const transport = successTransport(fixtureItems('transcript-success.synthetic.json'));
  await getTranscript(`${URL}&mibextid=tracking`, { token: 'test-token', transport, maxTotalChargeUsd: '0.10' });

  assert.equal(transport.postCount, 1);
  const post = transport.requests[0];
  assert.equal(post.path, '/acts/apple_yang~facebook-transcript-scraper-api/runs');
  assert.deepEqual(post.body, { videoUrl: URL });
  assert.equal(post.query.restartOnError, 'false');
  assert.equal(post.query.build, '0.0.18');
  assert.equal(post.query.maxTotalChargeUsd, 0.1);
  assert.ok(transport.requests.slice(1).every((request) => request.method === 'GET'));
});

test('unknown and undocumented item fields are preserved', async () => {
  const transport = successTransport(fixtureItems('extra-fields.synthetic.json'));
  const result = await getTranscript(URL, { token: 'test-token', transport });
  assert.deepEqual(result.items[0].someFutureField, { nested: true });
  assert.equal(result.items[0].likesCount, 3);
  assert.equal(result.items[0].shareCount, 2);
});

test('malformed segments are dropped only from the normalized view', async () => {
  const transport = successTransport(fixtureItems('segments-invalid.synthetic.json'));
  const result = await getTranscript(URL, { token: 'test-token', transport });
  assert.deepEqual(result.segments, [
    { start: 0, end: 1.2, text: 'valid one' },
    { start: 4, end: 5, text: 'valid two' },
  ]);
  assert.equal(result.items[0].segments.length, 7);
});

test('actor_error wins even when text is present', async () => {
  const transport = successTransport(fixtureItems('transcript-actor-error.synthetic.json'));
  const result = await getTranscript(URL, { token: 'test-token', transport });
  assert.equal(result.status, 'actor_error');
  assert.equal(result.succeeded, false);
  assert.match(result.error, /not available in this region/);
});

test('null text is no_transcript and a numeric text is unknown', async () => {
  const nullResult = await getTranscript(URL, {
    token: 'test-token',
    transport: successTransport(fixtureItems('no-transcript-null.synthetic.json')),
  });
  assert.equal(nullResult.status, 'no_transcript');

  const missingResult = await getTranscript(URL, {
    token: 'test-token',
    transport: successTransport(fixtureItems('no-transcript-missing.synthetic.json')),
  });
  assert.equal(missingResult.status, 'no_transcript');

  const unknownResult = await getTranscript(URL, {
    token: 'test-token',
    transport: successTransport(fixtureItems('unknown-text-type.synthetic.json')),
  });
  assert.equal(unknownResult.status, 'unknown');
});

test('run_failed is returned, not raised', async () => {
  const transport = new FakeTransport([
    { data: { id: 'run-1', defaultDatasetId: 'ds-1', buildNumber: '0.0.18', buildId: APPROVED_BUILD_ID } },
    { data: { id: 'run-1', status: 'FAILED', defaultDatasetId: 'ds-1' } },
  ]);
  const result = await getTranscript(URL, { token: 'test-token', transport });
  assert.equal(result.status, 'run_failed');
  assert.match(result.error, /FAILED/);
  assert.equal(transport.postCount, 1);
});

test('ambiguous create is not retried', async () => {
  for (const error of [
    new ApiError('timed out', { ambiguous: true }),
    new ApiError('Apify HTTP 500', { status: 500, ambiguous: true }),
  ]) {
    const transport = new FakeTransport([error]);
    await assert.rejects(
      getTranscript(URL, { token: 'test-token', transport }),
      CreationUnknownError,
    );
    assert.equal(transport.postCount, 1);
  }
});

test('definite create rejection is a transport error', async () => {
  const transport = new FakeTransport([new ApiError('Apify HTTP 400', { status: 400 })]);
  await assert.rejects(getTranscript(URL, { token: 'test-token', transport }), TransportError);
  assert.equal(transport.postCount, 1);
});

test('build mismatch raises ProtocolError with the run id', async () => {
  const transport = successTransport(fixtureItems('transcript-success.synthetic.json'), {
    buildNumber: '0.0.17',
  });
  await assert.rejects(getTranscript(URL, { token: 'test-token', transport }), (error) => {
    assert.ok(error instanceof ProtocolError);
    assert.equal(error.runId, 'run-synthetic');
    return true;
  });
});

test('resume never posts', async () => {
  const transport = new FakeTransport([
    { data: { id: 'run-existing', status: 'SUCCEEDED', defaultDatasetId: 'ds-existing', buildNumber: '0.0.18', buildId: APPROVED_BUILD_ID } },
    fixtureItems('transcript-success.synthetic.json'),
  ]);
  const result = await getTranscript(URL, { token: 'test-token', transport, runId: 'run-existing' });
  assert.equal(result.status, 'success');
  assert.equal(transport.postCount, 0);
  assert.equal(transport.requests[0].path, '/actor-runs/run-existing');
});

test('configuration errors send no request', async () => {
  const transport = new FakeTransport([]);
  await assert.rejects(getTranscript(URL, { token: 'test-token', transport, requireChargeCap: true }), ConfigurationError);
  assert.equal(transport.postCount, 0);

  const saved = process.env.APIFY_TOKEN;
  delete process.env.APIFY_TOKEN;
  try {
    await assert.rejects(getTranscript(URL, { transport }), ConfigurationError);
  } finally {
    if (saved !== undefined) process.env.APIFY_TOKEN = saved;
  }
  assert.equal(transport.requests.length, 0);
});

test('invalid runId is rejected', async () => {
  await assert.rejects(
    getTranscript(URL, { token: 'test-token', transport: new FakeTransport([]), runId: ' run-1' }),
    ConfigurationError,
  );
});

await runTests();
