import { readFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import { buildApp } from '../src/index.js';
import { pool, checkDbReady } from '../src/db.js';
import type { FastifyInstance } from 'fastify';

const __dirname = dirname(fileURLToPath(import.meta.url));
const fixturesDir = resolve(__dirname, 'fixtures');

function loadFixture<T>(name: string): T {
  return JSON.parse(readFileSync(resolve(fixturesDir, name), 'utf8')) as T;
}

/** Compare payloads ignoring key order; tolerate tiny float noise. */
function expectCloseToFixture(actual: unknown, expected: unknown, path = '$'): void {
  if (Array.isArray(expected)) {
    expect(Array.isArray(actual), `${path} should be array`).toBe(true);
    const a = actual as unknown[];
    expect(a.length, `${path}.length`).toBe(expected.length);
    for (let i = 0; i < expected.length; i++) {
      expectCloseToFixture(a[i], expected[i], `${path}[${i}]`);
    }
    return;
  }
  if (expected !== null && typeof expected === 'object') {
    expect(actual !== null && typeof actual === 'object', `${path} should be object`).toBe(true);
    const e = expected as Record<string, unknown>;
    const a = actual as Record<string, unknown>;
    for (const key of Object.keys(e)) {
      expect(key in a, `${path}.${key} missing`).toBe(true);
      expectCloseToFixture(a[key], e[key], `${path}.${key}`);
    }
    return;
  }
  if (typeof expected === 'number' && typeof actual === 'number') {
    expect(Math.abs(actual - expected)).toBeLessThan(0.011);
    return;
  }
  expect(actual, path).toEqual(expected);
}

describe('API parity with Flask fixtures', () => {
  let app: FastifyInstance;
  let dbReady = false;

  beforeAll(async () => {
    dbReady = await checkDbReady();
    if (!dbReady) return;
    app = await buildApp();
    await app.ready();
  });

  afterAll(async () => {
    if (app) await app.close();
    await pool.end();
  });

  it('matches /api/conferences', async () => {
    if (!dbReady) return;
    const res = await app.inject({ method: 'GET', url: '/api/conferences' });
    expect(res.statusCode).toBe(200);
    expectCloseToFixture(res.json(), loadFixture('conferences.json'));
  });

  it('matches /api/seasons', async () => {
    if (!dbReady) return;
    const res = await app.inject({ method: 'GET', url: '/api/seasons' });
    expect(res.statusCode).toBe(200);
    expectCloseToFixture(res.json(), loadFixture('seasons.json'));
  });

  it('matches /api/pitchers?limit=10', async () => {
    if (!dbReady) return;
    const res = await app.inject({ method: 'GET', url: '/api/pitchers?limit=10' });
    expect(res.statusCode).toBe(200);
    expectCloseToFixture(res.json(), loadFixture('pitchers-default.json'));
  });

  it('matches /api/hitters?limit=10', async () => {
    if (!dbReady) return;
    const res = await app.inject({ method: 'GET', url: '/api/hitters?limit=10' });
    expect(res.statusCode).toBe(200);
    expectCloseToFixture(res.json(), loadFixture('hitters-default.json'));
  });

  it('matches filtered pitchers', async () => {
    if (!dbReady) return;
    const res = await app.inject({
      method: 'GET',
      url: '/api/pitchers?limit=5&min_ip=20%2B&drafted=drafted&season=2025',
    });
    expect(res.statusCode).toBe(200);
    expectCloseToFixture(res.json(), loadFixture('pitchers-filtered.json'));
  });

  it('matches filtered hitters', async () => {
    if (!dbReady) return;
    const res = await app.inject({
      method: 'GET',
      url: '/api/hitters?limit=5&min_ab=100&drafted=not_drafted&season=2025',
    });
    expect(res.statusCode).toBe(200);
    expectCloseToFixture(res.json(), loadFixture('hitters-filtered.json'));
  });

  it('serves health', async () => {
    if (!dbReady) return;
    const res = await app.inject({ method: 'GET', url: '/health' });
    expect(res.statusCode).toBe(200);
    expect(res.json()).toEqual({ status: 'ok' });
  });
});
