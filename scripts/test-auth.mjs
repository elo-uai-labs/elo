import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { mkdtemp, rm, writeFile, mkdir } from 'node:fs/promises';
import { randomBytes } from 'node:crypto';
import { tmpdir } from 'node:os';
import path from 'node:path';
import net from 'node:net';
import { setTimeout as delay } from 'node:timers/promises';

const root = path.resolve(import.meta.dirname, '..');
const temporary = await mkdtemp(path.join(tmpdir(), 'elo-auth-e2e-'));
const probe = net.createServer();
probe.listen(0, '127.0.0.1');
await once(probe, 'listening');
const port = probe.address().port;
await new Promise((resolve) => probe.close(resolve));
const credentials = Object.fromEntries(['analyst', 'reviewer', 'operator', 'auditor', 'admin'].map((role) => [role, randomBytes(24).toString('base64url')]));
const url = `http://127.0.0.1:${port}`;
const env = { ...process.env, ELO_API_PORT: String(port), ELO_DB: path.join(temporary, 'auth.sqlite3'), ELO_URL: url,
  ELO_AUTH_USERS_FILE: path.join(temporary, 'users.json'), ELO_TEST_AUTH_PASSWORDS: JSON.stringify(credentials),
  PYTHONPATH: path.join(root, 'backend'),
};
let server;
let serverLogs = '';
async function run(command, args) {
  const child = spawn(command, args, { cwd: root, env, stdio: 'inherit' });
  const [code] = await once(child, 'exit');
  assert.equal(code, 0, `${path.basename(command)} ${args[0]}`);
}
try {
  await run('python3', ['-c', `import os,json
from access import provision
names={'analyst':'Analista Sintético','reviewer':'Revisora Sintética','operator':'Operador Sintético','auditor':'Auditoria Sintética','admin':'Administração Sintética'}
for role,password in json.loads(os.environ['ELO_TEST_AUTH_PASSWORDS']).items():
    provision(os.environ['ELO_AUTH_USERS_FILE'],role,names[role],[role],password)
`]);
  await run(process.execPath, ['node_modules/vite/bin/vite.js', 'build']);
  server = spawn(process.execPath, ['scripts/start.mjs'], { cwd: root, env, stdio: ['ignore', 'pipe', 'pipe'] });
  server.stdout.on('data', (data) => { serverLogs += data; });
  server.stderr.on('data', (data) => { serverLogs += data; });
  let ready = false;
  for (let attempt = 0; attempt < 100; attempt++) {
    if (server.exitCode !== null) throw new Error('Servidor autenticado não iniciou.');
    try { if ((await fetch(`${url}/health`)).ok) { ready = true; break; } } catch {}
    await delay(100);
  }
  assert.ok(ready, 'Servidor autenticado precisa iniciar.');
  await run(process.execPath, ['tests/browser-auth.cjs']);
  await mkdir(path.join(root, 'output/validation'), { recursive: true });
  await writeFile(path.join(root, 'output/validation/result-auth.json'), JSON.stringify({
    date: new Date().toISOString(), mode: 'local-auth', synthetic: true, temporaryIdentities: true,
    roles: Object.keys(credentials), desktop: true, mobile: true, canonicalActors: true,
    permissionsEnforced: true, independentReview: true, assignmentEnforced: true, logoutRevokesAccess: true,
  }, null, 2));
  console.log('Elo: login local, identidades canônicas, perfis, atribuição, revisão independente e logout verificados.');
} catch (error) {
  if (serverLogs) console.error('Diagnóstico do servidor autenticado isolado:\n' + serverLogs);
  throw error;
} finally {
  if (server && server.exitCode === null) {
    const closed = once(server, 'exit');
    server.kill('SIGTERM');
    await closed;
  }
  await rm(temporary, { recursive: true, force: true });
}
