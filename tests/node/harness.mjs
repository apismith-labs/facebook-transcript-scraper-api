import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
export const FIXTURE_DIR = resolve(HERE, '../fixtures');

export function fixtureItems(name) {
  return JSON.parse(readFileSync(resolve(FIXTURE_DIR, name), 'utf8')).items;
}

export class FakeTransport {
  constructor(responses = []) {
    this.responses = [...responses];
    this.requests = [];
  }

  async request(method, path, body, options = {}) {
    this.requests.push({ method, path, body, query: options.query });
    if (!this.responses.length) throw new Error('No synthetic transport response queued');
    const response = this.responses.shift();
    if (response instanceof Error) throw response;
    return response;
  }

  get postCount() {
    return this.requests.filter((request) => request.method === 'POST').length;
  }

  get paths() {
    return this.requests.map((request) => request.path);
  }
}

const tests = [];

export function test(name, fn) {
  tests.push({ name, fn });
}

export async function runTests() {
  let failed = 0;
  for (const { name, fn } of tests) {
    try {
      await fn();
      console.log(`ok - ${name}`);
    } catch (error) {
      failed += 1;
      console.error(`not ok - ${name}`);
      console.error(error?.stack || error);
    }
  }
  console.log(`\n${tests.length - failed}/${tests.length} passed`);
  if (failed) process.exitCode = 1;
}
