#!/usr/bin/env node
/** Quick start: one public Facebook video URL in, transcript text out. */
import {
  APPROVED_BUILD_NUMBER,
  ConfigurationError,
  CreationUnknownError,
  ProtocolError,
  TransportError,
  getTranscript,
} from './client.mjs';
import { EXIT_CODES } from './reliable-actor.mjs';

async function main() {
  const url = process.argv[2];
  if (!url || url === '--help' || url === '-h') {
    console.log("Usage: node examples/nodejs/quickstart-single.mjs '<public Facebook video URL>'");
    return url ? 1 : 2;
  }
  try {
    const result = await getTranscript(url, { build: APPROVED_BUILD_NUMBER });
    console.log(`Run ID: ${result.runId}`);
    console.log(`Status: ${result.status}`);
    if (result.status === 'success') {
      console.log('Transcript:');
      console.log(result.text);
    } else {
      console.log(result.error || 'No transcript text');
    }
    return EXIT_CODES[result.status] ?? 1;
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
      console.error(`Protocol error: ${error.message}`);
      return 3;
    }
    if (error instanceof TransportError) {
      console.error(`Transport error: ${error.message}`);
      return EXIT_CODES.transport_error;
    }
    throw error;
  }
}

process.exitCode = await main();
