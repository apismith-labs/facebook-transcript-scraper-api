#!/usr/bin/env node
/**
 * One independent Actor Run per non-empty CSV row.
 *
 * Without --execute this script only validates the file and prints a plan: it reads no token and
 * creates no Run.
 */
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
  validateVideoUrl,
} from './client.mjs';
import { DATASET_ITEM_USD, TIER_PRICES_USD_PER_MINUTE, billedMinutes } from './cost.mjs';
import { EXIT_CODES, RunJournal, sanitize, summarize, writePrivate } from './reliable-actor.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));

export function splitCsvLine(line) {
  const fields = [];
  let current = '';
  let quoted = false;
  for (let index = 0; index < line.length; index += 1) {
    const char = line[index];
    if (quoted) {
      if (char === '"') {
        if (line[index + 1] === '"') {
          current += '"';
          index += 1;
        } else {
          quoted = false;
        }
      } else {
        current += char;
      }
    } else if (char === '"') {
      quoted = true;
    } else if (char === ',') {
      fields.push(current);
      current = '';
    } else {
      current += char;
    }
  }
  fields.push(current);
  return fields;
}

export function parseRows(path) {
  if (!existsSync(path)) throw new ConfigurationError(`CSV file not found: ${path}`);
  const text = readFileSync(path, 'utf8').replace(/^\uFEFF/, '');
  const lines = text.split(/\r?\n/);
  if (!lines.length || !lines[0].trim()) throw new ConfigurationError('CSV must start with a header row');
  const header = splitCsvLine(lines[0]).map((name) => name.trim().toLowerCase());
  const urlIndex = header.indexOf('videourl') >= 0 ? header.indexOf('videourl') : header.indexOf('url');
  if (urlIndex < 0) throw new ConfigurationError("CSV must have a 'videoUrl' or 'url' column");
  const durationIndex = header.indexOf('durationseconds');

  const rows = [];
  for (let index = 1; index < lines.length; index += 1) {
    const line = lines[index];
    if (!line.trim()) continue;
    const fields = splitCsvLine(line);
    const rowId = String(index + 1);
    const url = (fields[urlIndex] ?? '').trim();
    if (!url) continue;
    let canonical;
    try {
      canonical = validateVideoUrl(url);
    } catch (error) {
      throw new ConfigurationError(`CSV line ${rowId}: ${error.message}`);
    }
    let durationSeconds = null;
    if (durationIndex >= 0) {
      const raw = (fields[durationIndex] ?? '').trim();
      if (raw) {
        const value = Number(raw);
        if (!Number.isFinite(value) || value < 0) {
          throw new ConfigurationError(`CSV line ${rowId}: durationSeconds must be a non-negative number`);
        }
        durationSeconds = value;
      }
    }
    rows.push({
      rowId,
      url,
      canonicalUrl: canonical.canonicalUrl,
      form: canonical.form,
      durationSeconds,
    });
  }
  if (!rows.length) throw new ConfigurationError('CSV contains no non-empty URL rows');
  return rows;
}

export function estimateRows(rows, tier) {
  const selected = String(tier || 'FREE').trim().toUpperCase();
  if (!(selected in TIER_PRICES_USD_PER_MINUTE)) {
    throw new ConfigurationError(`tier must be one of ${Object.keys(TIER_PRICES_USD_PER_MINUTE).join(', ')}`);
  }
  const minutes = rows.reduce((sum, row) => sum + billedMinutes(row.durationSeconds ?? 0), 0);
  const datasetItemUsd = DATASET_ITEM_USD * rows.length;
  const speechToTextUsd = TIER_PRICES_USD_PER_MINUTE[selected] * minutes;
  return {
    tier: selected,
    videos: rows.length,
    billedMinutes: minutes,
    datasetItemUsd,
    speechToTextUsd,
    totalUsd: datasetItemUsd + speechToTextUsd,
    lowerBound: rows.some((row) => row.durationSeconds === null),
  };
}

export async function runBatch(rows, options) {
  const {
    token,
    actorId,
    build = APPROVED_BUILD_NUMBER,
    maxConcurrency = 3,
    timeout = 900,
    maxTotalChargeUsd,
    requireChargeCap = false,
    datasetLimit = 100,
    journal,
    transportFactory,
  } = options;
  if (!Number.isInteger(maxConcurrency) || maxConcurrency < 1) {
    throw new ConfigurationError('maxConcurrency must be a positive integer');
  }

  const results = new Array(rows.length);
  let cursor = 0;
  const worker = async () => {
    while (true) {
      const index = cursor;
      cursor += 1;
      if (index >= rows.length) return;
      const row = rows[index];
      const base = {
        rowId: row.rowId,
        sourceUrl: row.url,
        canonicalUrl: row.canonicalUrl,
        urlForm: row.form,
      };
      try {
        const result = await getTranscript(row.url, {
          token,
          actorId,
          build,
          timeout,
          maxTotalChargeUsd,
          requireChargeCap,
          datasetLimit,
          rowId: row.rowId,
          transport: transportFactory ? transportFactory() : undefined,
          journal,
        });
        results[index] = {
          ...base,
          status: result.status,
          runId: result.runId,
          datasetId: result.datasetId,
          title: result.title,
          duration: result.duration,
          nickname: result.nickname,
          text: result.text,
          segments: result.segments,
          items: result.items,
          datasetComplete: result.datasetComplete,
          error: result.error,
        };
      } catch (error) {
        if (error instanceof CreationUnknownError) {
          results[index] = { ...base, status: 'creation_unknown', error: error.message };
        } else if (error instanceof ConfigurationError || error instanceof ProtocolError) {
          results[index] = {
            ...base,
            status: 'unknown',
            error: error.message,
            ...(error.runId ? { runId: error.runId } : {}),
            ...(error.datasetId ? { datasetId: error.datasetId } : {}),
          };
        } else if (error instanceof TransportError) {
          results[index] = {
            ...base,
            status: 'transport_error',
            error: error.message,
            ...(error.runId ? { runId: error.runId } : {}),
          };
        } else {
          throw error;
        }
      }
    }
  };

  const workerCount = Math.min(maxConcurrency, rows.length);
  await Promise.all(Array.from({ length: workerCount }, worker));
  return results;
}

function uniquePath(path) {
  if (!existsSync(path)) return path;
  const stem = path.replace(/\.json$/, '');
  for (let index = 1; index < 1000; index += 1) {
    const candidate = `${stem}-${index}.json`;
    if (!existsSync(candidate)) return candidate;
  }
  throw new ConfigurationError('could not allocate a unique result filename');
}

function timestamp() {
  return new Date().toISOString().replace(/[-:]/g, '').replace(/\.\d{3}Z$/, 'Z');
}

async function main() {
  let values;
  let positionals;
  try {
    ({ values, positionals } = parseArgs({
      args: process.argv.slice(2),
      allowPositionals: true,
      options: {
        execute: { type: 'boolean', default: false },
        limit: { type: 'string' },
        'max-concurrency': { type: 'string', default: '3' },
        output: { type: 'string' },
        tier: { type: 'string', default: 'FREE' },
        timeout: { type: 'string', default: '900' },
        build: { type: 'string', default: APPROVED_BUILD_NUMBER },
        'actor-id': { type: 'string' },
        'dataset-limit': { type: 'string', default: '100' },
        'max-total-charge-usd': { type: 'string' },
        'require-charge-cap': { type: 'boolean', default: false },
      },
    }));
  } catch (error) {
    console.error(`Argument error: ${error.message}`);
    return 2;
  }
  if (positionals.length !== 1) {
    console.error('Usage: node examples/nodejs/batch-csv.mjs <file.csv> [--execute]');
    return 2;
  }

  const csvPath = resolve(positionals[0]);
  let rows;
  let estimate;
  try {
    rows = parseRows(csvPath);
    if (values.limit !== undefined) {
      const limit = Number(values.limit);
      if (!Number.isInteger(limit) || limit < 1) throw new ConfigurationError('--limit must be a positive integer');
      rows = rows.slice(0, limit);
    }
    estimate = estimateRows(rows, values.tier);
  } catch (error) {
    console.error(`Configuration error: ${error.message}`);
    return 2;
  }

  console.log(`CSV: ${csvPath}`);
  console.log(`Rows: ${rows.length}`);
  console.log(
    `Estimate: ${estimate.videos} video(s), ${estimate.billedMinutes} billed minute(s), ${estimate.tier} tier ` +
      `-> $${estimate.totalUsd.toFixed(4)} estimated ` +
      `(dataset $${estimate.datasetItemUsd.toFixed(4)} + speech $${estimate.speechToTextUsd.toFixed(4)})` +
      (estimate.lowerBound ? ' [lower bound: some durations unknown]' : ''),
  );

  if (!values.execute) {
    console.log('Plan only. No Run was created and no token was read.');
    console.log('Re-run with --execute to process these rows.');
    return 0;
  }

  const token = process.env.APIFY_TOKEN;
  if (!token || !token.trim()) {
    console.error('Configuration error: APIFY_TOKEN is required when --execute is used');
    return 2;
  }

  const resultPath = uniquePath(
    values.output
      ? resolve(values.output)
      : resolve(dirname(csvPath), `facebook-batch-results-${timestamp()}.json`),
  );
  const journal = new RunJournal(resolve(dirname(resultPath), 'nodejs-run-journal.jsonl'));

  let results;
  try {
    results = await runBatch(rows, {
      token,
      actorId: values['actor-id'],
      build: values.build,
      maxConcurrency: Number(values['max-concurrency']),
      timeout: Number(values.timeout),
      maxTotalChargeUsd: values['max-total-charge-usd'],
      requireChargeCap: values['require-charge-cap'],
      datasetLimit: Number(values['dataset-limit']),
      journal,
    });
  } catch (error) {
    console.error(`Configuration error: ${error.message}`);
    return 2;
  }

  const counts = summarize(results);
  const payload = sanitize({
    generatedAt: new Date().toISOString(),
    actorId: values['actor-id'] ?? process.env.APIFY_ACTOR_ID ?? 'apple_yang/facebook-transcript-scraper-api',
    build: values.build,
    source: csvPath,
    estimate,
    counts,
    results,
  });
  writePrivate(resultPath, `${JSON.stringify(payload, null, 2)}\n`);
  console.log(`Result: ${resultPath}`);
  console.log(`Counts: ${Object.entries(counts).map(([key, value]) => `${key}=${value}`).join(', ')}`);
  const failed = results.filter((row) => row.status !== 'success').map((row) => row.rowId);
  if (failed.length) {
    console.error(`Non-success rows: ${failed.join(', ')}`);
    return 1;
  }
  return 0;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  process.exitCode = await main();
}
