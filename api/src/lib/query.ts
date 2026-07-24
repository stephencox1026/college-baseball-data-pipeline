import type { FastifyRequest } from 'fastify';
import { z } from 'zod';
import type { MinIpRange } from '../types.js';

const MAX_LIMIT = 200;

function asArray(value: string | string[] | undefined): string[] {
  if (value === undefined) return [];
  return Array.isArray(value) ? value : [value];
}

function parseIntList(value: string | string[] | undefined): number[] | undefined {
  const raw = asArray(value);
  if (!raw.length) return undefined;
  const nums = raw.map((v) => Number.parseInt(v, 10)).filter((n) => Number.isFinite(n));
  return nums.length ? nums : undefined;
}

export function parseLimit(query: FastifyRequest['query']): number {
  const q = query as Record<string, string | string[] | undefined>;
  const raw = Array.isArray(q.limit) ? q.limit[0] : q.limit;
  const n = raw ? Number.parseInt(raw, 10) : 50;
  if (!Number.isFinite(n) || n < 1) return 50;
  return Math.min(n, MAX_LIMIT);
}

export function parseSharedFilters(query: FastifyRequest['query']) {
  const q = query as Record<string, string | string[] | undefined>;
  return {
    limit: parseLimit(query),
    conferenceId: parseIntList(q.conference_id),
    drafted: (() => {
      const d = asArray(q.drafted);
      return d.length ? d : undefined;
    })(),
    season: parseIntList(q.season),
    age: parseIntList(q.age),
  };
}

const minIpSchema = z.enum(['0-10', '11-20', '20+']);

export function parseMinIp(query: FastifyRequest['query']): MinIpRange {
  const q = query as Record<string, string | string[] | undefined>;
  const raw = Array.isArray(q.min_ip) ? q.min_ip[0] : q.min_ip;
  const parsed = minIpSchema.safeParse(raw ?? '20+');
  return parsed.success ? parsed.data : '20+';
}

export function parseMinAb(query: FastifyRequest['query']): number {
  const q = query as Record<string, string | string[] | undefined>;
  const raw = Array.isArray(q.min_ab) ? q.min_ab[0] : q.min_ab;
  const n = raw ? Number.parseInt(raw, 10) : 100;
  if (!Number.isFinite(n) || n < 0) return 100;
  return n;
}
