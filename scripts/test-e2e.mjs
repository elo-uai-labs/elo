import assert from 'node:assert/strict';
import { spawn, execFileSync } from 'node:child_process';
import { existsSync } from 'node:fs';
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
const env = { ...process.env, ELO_ENV: 'test', ELO_REQUIRE_AUTH: '0', ELO_AUTH_USERS_FILE: '', ELO_API_PORT: String(port), ELO_DB: path.join(temporary, 'test.sqlite3'), ELO_URL: url };
let server;
let serverLogs = '';

async function run(args) {
  const child = spawn(process.execPath, args, { cwd: root, env, stdio: 'inherit' });
  const [code] = await once(child, 'exit');
  assert.equal(code, 0, args.join(' '));
}
async function start() {
  server = spawn(process.execPath, ['scripts/start.mjs'], { cwd: root, env, stdio: ['ignore', 'pipe', 'pipe'] });
  serverLogs = '';
  server.stdout.on('data', (data) => { serverLogs += data; });
  server.stderr.on('data', (data) => { serverLogs += data; });
  for (let attempt = 0; attempt < 100; attempt++) {
    if (server.exitCode !== null) throw new Error(`Servidor não iniciou: ${serverLogs}`);
    try { if ((await fetch(`${url}/health`)).ok) return; } catch {}
    await delay(100);
  }
  throw new Error(`Timeout ao iniciar servidor: ${serverLogs}`);
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
  const auditResponse = await fetch(`${url}/api/audit/export`);
  assert.ok(auditResponse.ok, 'Exportação final com documentos e importações');
  const auditPath = path.join(temporary, 'diagnostic-audit.json');
  await writeFile(auditPath, await auditResponse.text());
  execFileSync(env.PYTHON || (existsSync(path.join(root, '.venv/bin/python3')) ? path.join(root, '.venv/bin/python3') : 'python3'),
    ['backend/audit_export.py', auditPath], {cwd: root, env, stdio: 'inherit'});
  const before = await (await fetch(`${url}/api/state`)).json();
  if (before.case.dossier.usage?.provider === 'openai') {
    const usageReport = JSON.parse(execFileSync(env.PYTHON || (existsSync(path.join(root, '.venv/bin/python3')) ? path.join(root, '.venv/bin/python3') : 'python3'),
      ['backend/ai_usage.py', auditPath], {cwd: root, env, encoding: 'utf8'}));
    assert.ok(usageReport.totals.total_tokens.measured_records > 0, 'Rodada OpenAI real deve informar tokens');
    assert.ok(usageReport.records.some(row => row.kind === 'assistant' && row.usage?.total_tokens != null), 'Consumo do assistente preservado');
    await mkdir(path.join(root, 'output/validation'), { recursive: true });
    await writeFile(path.join(root, 'output/validation/usage-report-real.json'), JSON.stringify(usageReport, null, 2));
  }

  await stop();
  await start();
  const after = await (await fetch(`${url}/api/state`)).json();
  assert.deepEqual(after, before, 'Estado deve persistir após reiniciar o processo');
  assert.equal(after.audit_valid, true);
  await mkdir(path.join(root, 'output/validation'), { recursive: true });
  const result = JSON.stringify({
    date: new Date().toISOString(), designSystem: '4.10.1', dossierMode: after.case.dossier.mode,
    model: after.case.dossier.model, caseId: after.case.id, auditEvents: after.audit.length,
    auditValid: after.audit_valid, restartPersistence: true, desktop: true, mobile: true,
    promptVersion: after.case.dossier.prompt_version, cases: after.cases.length,
    risks: after.risks.length, assessments: after.assessments.length,
  }, null, 2);
  await writeFile(path.join(root, 'output/validation/result.json'), result);
  await writeFile(path.join(root, `output/validation/result-${after.case.dossier.mode}.json`), result);
  console.log('Build, jornada completa, Porsche Next, celular, indicadores e persistência após reiniciar: OK.');
} catch (error) {
  if (serverLogs) console.error('Diagnóstico do servidor isolado:\n' + serverLogs);
  throw error;
} finally {
  await stop();
  await rm(temporary, { recursive: true, force: true });
}
