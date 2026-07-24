import Fastify from 'fastify';
import cors from '@fastify/cors';
import fastifyStatic from '@fastify/static';
import { readFile } from 'node:fs/promises';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { randomUUID } from 'node:crypto';
import { pool } from './db.js';
import { registerRoutes } from './routes/api.js';
import { getConferences } from './services/ranking.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const projectRoot = resolve(__dirname, '../..');
const templatesDir = resolve(projectRoot, 'templates');
const staticDir = resolve(projectRoot, 'static');

export async function buildApp() {
  const app = Fastify({
    logger: {
      level: process.env.LOG_LEVEL ?? 'info',
    },
    genReqId: () => randomUUID(),
    requestIdHeader: 'x-request-id',
  });

  await app.register(cors, { origin: true });

  app.addHook('onRequest', async (req, reply) => {
    reply.header('x-request-id', req.id);
  });

  await registerRoutes(app);

  await app.register(fastifyStatic, {
    root: staticDir,
    prefix: '/static/',
    decorateReply: false,
  });

  app.get('/', async (_req, reply) => {
    const conferences = await getConferences();
    const template = await readFile(resolve(templatesDir, 'dashboard.html'), 'utf8');

    const pitcherChecks = conferences
      .map(
        (c) =>
          `<div class="filter-option"><input type="checkbox" value="${c.id}" id="pitcher-conf-${c.id}"> <label for="pitcher-conf-${c.id}">${c.name}</label></div>`,
      )
      .join('\n                        ');
    const hitterChecks = conferences
      .map(
        (c) =>
          `<div class="filter-option"><input type="checkbox" value="${c.id}" id="hitter-conf-${c.id}"> <label for="hitter-conf-${c.id}">${c.name}</label></div>`,
      )
      .join('\n                        ');

    let html = template;
    html = html.replace(
      /\{%\s*for conf in conferences\s*%\}[\s\S]*?\{%\s*endfor\s*%\}/,
      pitcherChecks,
    );
    html = html.replace(
      /\{%\s*for conf in conferences\s*%\}[\s\S]*?\{%\s*endfor\s*%\}/,
      hitterChecks,
    );
    return reply.type('text/html').send(html);
  });

  return app;
}

async function main() {
  const port = Number(process.env.PORT ?? 8080);
  const host = process.env.HOST ?? '0.0.0.0';
  const app = await buildApp();

  const shutdown = async () => {
    await app.close();
    await pool.end();
    process.exit(0);
  };
  process.on('SIGINT', shutdown);
  process.on('SIGTERM', shutdown);

  await app.listen({ port, host });
}

const isDirectRun =
  process.argv[1] &&
  fileURLToPath(import.meta.url) === resolve(process.argv[1]);

if (isDirectRun) {
  main().catch((err) => {
    console.error(err);
    process.exit(1);
  });
}
