import type { FastifyInstance } from 'fastify';
import { checkDbReady } from '../db.js';
import {
  getConferences,
  getSeasons,
  getTopHitters,
  getTopPitchers,
} from '../services/ranking.js';
import { parseMinAb, parseMinIp, parseSharedFilters } from '../lib/query.js';

export async function registerRoutes(app: FastifyInstance): Promise<void> {
  app.get('/health', async () => ({ status: 'ok' }));

  app.get('/ready', async (_req, reply) => {
    const ready = await checkDbReady();
    if (!ready) {
      return reply.code(503).send({ status: 'not_ready' });
    }
    return { status: 'ready' };
  });

  app.get('/api/conferences', async () => getConferences());

  app.get('/api/seasons', async () => getSeasons());

  app.get('/api/pitchers', async (req, reply) => {
    try {
      const shared = parseSharedFilters(req.query);
      const minIp = parseMinIp(req.query);
      return await getTopPitchers({ ...shared, minIp });
    } catch (err) {
      req.log.error(err);
      return reply.code(500).send({ error: err instanceof Error ? err.message : String(err) });
    }
  });

  app.get('/api/hitters', async (req, reply) => {
    try {
      const shared = parseSharedFilters(req.query);
      const minAb = parseMinAb(req.query);
      return await getTopHitters({ ...shared, minAb });
    } catch (err) {
      req.log.error(err);
      return reply.code(500).send({ error: err instanceof Error ? err.message : String(err) });
    }
  });
}
