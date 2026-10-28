#!/usr/bin/env node
/** Run one public Facebook video URL and print its transcript. */
import { existsSync, readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseArgs } from 'node:util';

import {
  APPROVED_BUILD_NUMBER,
  ConfigurationError,
  CreationUnknownError,
  ProtocolError,
  TransportError,
  getTranscript,
} from './client.mjs';
import {
  EXIT_CODES,
  RunJournal,
  loadResumeRecord,
  sanitize,
  writePrivate,
} from './reliable-actor.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(HERE, '../..');
const JOURNAL_PATH = resolve(REPO_ROOT, 'sample-output/generated/nodejs-run-journal.jsonl');

function loadEnvFile(path) {
  if (!existsSync(path)) return;
  for (const line of readFileSync(path, 'utf8').split('\n')) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#') || !trimmed.includes('=')) continue;
    const index = trimmed.indexOf('=');
    const key = trimmed.slice(0, index).trim();
    const value = trimmed.slice(index + 1).trim().replace(/^["']|["']$/g, '');
    if (key.startsWith('APIFY_') && process.env[key] === undefined) process.env[key] = value;
  }
}

function parseCli(argv) {
  const { values, positionals } = parseArgs({
    args: argv,
    allowPositionals: true,
    options: {
      resume: { type: 'string' },
      json: { type: 'boolean', default: false },
      output: { type: 'string' },
      'dataset-limit': { type: 'string' },
      timeout: { type: 'string' },
      build: { type: 'string', default: APPROVED_BUILD_NUMBER },
      'actor-id': { type: 'string' },
      'max-total-charge-usd': { type: 'string' },
      'require-charge-cap': { type: 'boolean', default: false },
      'no-journal': { type: 'boolean', default: false },
      help: { type: 'boolean', short: 'h', default: false },
    },
  });
  return { values, positionals };
}

function usage() {
  console.log(
    "Usage: node examples/nodejs/single-url.mjs '<public Facebook video URL>' [--json] [--resume RUN_ID]",
  );
}

async function main() {
  loadEnvFile(resolve(process.cwd(), '.env'));
  let parsed;
  try {
    parsed = parseCli(process.argv.slice(2));
  } catch (error) {
    console.error(`Argument error: ${error.message}`);
    return 2;
  }
  const { values, positionals } = parsed;
  if (values.help) {
    usage();
    return 0;
  }
  if (positionals.length !== 1) {
    usage();
    return 2;
  }

  const url = positionals[0];
  const journal = values['no-journal'] ? null : new RunJournal(JOURNAL_PATH);
  if (values.resume && journal && existsSync(journal.path)) {
    try {
      const actorId = values['actor-id'] ?? process.env.APIFY_ACTOR_ID ?? 'apple_yang/facebook-transcript-scraper-api';
      const record = loadResumeRecord(journal, values.resume, actorId);
      if (record.sourceUrl && record.sourceUrl !== url) {
        console.error('Resume refused: the journal record belongs to a different source URL');
        return EXIT_CODES.transport_error;
      }
    } catch (error) {
      console.error(`Resume refused: ${error.message}`);
      return EXIT_CODES.transport_error;
    }
  }

  let result;
  try {
    result = await getTranscript(url, {
      build: values.build,
      timeout: values.timeout === undefined ? undefined : Number(values.timeout),
      maxTotalChargeUsd: values['max-total-charge-usd'],
      requireChargeCap: values['require-charge-cap'],
      datasetLimit: values['dataset-limit'] === undefined ? 100 : Number(values['dataset-limit']),
      runId: values.resume ?? null,
      actorId: values['actor-id'],
      journal: journal ?? undefined,
    });
  } catch (error) {
    if (error instanceof ConfigurationError) {
      console.error(`Configuration error: ${error.message}`);
      return 2;
    }
    if (error instanceof CreationUnknownError) {
      console.error(`Creation outcome unknown: ${error.message}`);
      return EXIT_CODES.creation_unknown;
    }
    if (error instanceof ProtocolError) {
      const suffix = error.runId ? ` (Run ${error.runId}, Dataset ${error.datasetId})` : '';
      console.error(`Protocol error: ${error.message}${suffix}`);
      return 3;
    }
    if (error instanceof TransportError) {
      const suffix = error.runId ? ` (Run ${error.runId})` : '';
      console.error(`Transport error: ${error.message}${suffix}`);
      return EXIT_CODES.transport_error;
    }
    throw error;
  }

  const payload = sanitize({
    status: result.status,
    text: result.text,
    segments: result.segments,
    items: result.items,
    runId: result.runId,
    datasetId: result.datasetId,
    sourceUrl: result.sourceUrl,
    canonicalUrl: result.canonicalUrl,
    urlForm: result.urlForm,
    title: result.title,
    duration: result.duration,
    nickname: result.nickname,
    datasetComplete: result.datasetComplete,
    error: result.error,
  });
  if (values.output) writePrivate(resolve(values.output), `${JSON.stringify(payload, null, 2)}\n`);

  if (values.json) {
    console.log(JSON.stringify(payload, null, 2));
  } else {
    console.log(`Run ID: ${result.runId ?? 'unknown'}`);
    console.log(`Status: ${result.status}`);
    if (result.title) console.log(`Video: ${result.title}`);
    if (result.duration !== null && result.duration !== undefined) console.log(`Duration: ${result.duration}s`);
    if (result.nickname) console.log(`Creator: ${result.nickname}`);
    console.log(`Segments: ${result.segments.length}`);
    if (result.status === 'success') {
      console.log('Transcript:');
      console.log(result.text);
    } else if (result.error) {
      console.log(`Detail: ${result.error}`);
    }
  }
  return EXIT_CODES[result.status] ?? 1;
}

process.exitCode = await main();
