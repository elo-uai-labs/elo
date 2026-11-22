import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { mkdtemp, rm, writeFile, mkdir } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import net from 'node:net';
import { setTimeout as delay } from 'node:timers/promises';

const root = path.resolve(import.meta.dirname, '..');
const temporary = await mkdtemp(path.join(tmpdir(), 'elo-e2e-'));
const probe = net.createServer();
probe.listen(0, '127.0.0.1');
await once(probe, 'listening');
const port = probe.address().port;
await new Promise((resolve) => probe.close(resolve));
const url = `http://127.0.0.1:${port}`;
const env = { ...process.env, ELO_API_PORT: String(port), ELO_DB: path.join(temporary, 'test.sqlite3'), ELO_URL: url };
let server;

async function run(args) {
  const child = spawn(process.execPath, args, { cwd: root, env, stdio: 'inherit' });
  const [code] = await once(child, 'exit');
  assert.equal(code, 0, args.join(' '));
}
async function start() {
  server = spawn(process.execPath, ['scripts/start.mjs'], { cwd: root, env, stdio: ['ignore', 'pipe', 'pipe'] });
  let logs = '';
  server.stdout.on('data', (data) => { logs += data; });
  server.stderr.on('data', (data) => { logs += data; });
  for (let attempt = 0; attempt < 100; attempt++) {
    if (server.exitCode !== null) throw new Error(`Servidor não iniciou: ${logs}`);
    try { if ((await fetch(`${url}/health`)).ok) return; } catch {}
    await delay(100);
  }
  throw new Error(`Timeout ao iniciar servidor: ${logs}`);
}
async function stop() {
  if (!server || server.exitCode !== null) return;
  const exited = once(server, 'exit');
  server.kill('SIGTERM');
  await exited;
}
try {
  await run(['node_modules/vite/bin/vite.js', 'build']);
  await start();
  await run(['tests/browser.cjs']);
  const before = await (await fetch(`${url}/api/state`)).json();
  await stop();
  await start();
  const after = await (await fetch(`${url}/api/state`)).json();
  assert.deepEqual(after, before, 'Estado deve persistir após reiniciar o processo');
  assert.equal(after.audit_valid, true);
  await mkdir(path.join(root, 'output/validation'), { recursive: true });
  await writeFile(path.join(root, 'output/validation/result.json'), JSON.stringify({
    date: new Date().toISOString(), designSystem: '4.10.1', dossierMode: after.case.dossier.mode,
    model: after.case.dossier.model, caseId: after.case.id, auditEvents: after.audit.length,
    auditValid: after.audit_valid, restartPersistence: true, desktop: true, mobile: true,
  }, null, 2));
  console.log('Build, jornada completa, Porsche Next, celular, indicadores e persistência após reiniciar: OK.');
} finally {
  await stop();
  await rm(temporary, { recursive: true, force: true });
}
