import { spawn } from 'node:child_process';
import { access, mkdir } from 'node:fs/promises';
import { constants, existsSync } from 'node:fs';
import { createServer } from 'node:net';
import { fileURLToPath, pathToFileURL } from 'node:url';
import path from 'node:path';

const root = fileURLToPath(new URL('../', import.meta.url));

async function freePort(port) {
  await new Promise((resolve, reject) => {
    const socket = createServer();
    socket.once('error', () => reject(new Error(`A porta ${port} está ocupada. Configure ELO_API_PORT / ELO_WEB_PORT ou encerre o servidor anterior.`)));
    socket.listen(port, '127.0.0.1', () => socket.close(resolve));
  });
}

function port(name, fallback) {
  const value = Number(process.env[name] || fallback);
  if (!Number.isInteger(value) || value < 1 || value > 65535) throw new Error(`${name} deve ser uma porta TCP válida.`);
  return value;
}

export async function launch({ production = false } = {}) {
  process.chdir(root);
  if (existsSync('.env')) process.loadEnvFile('.env');
  const apiPort = port('ELO_API_PORT', 8001);
  const webPort = port('ELO_WEB_PORT', 5173);
  if (!production && apiPort === webPort) throw new Error('Use portas diferentes para frontend e API.');
  await freePort(apiPort);
  if (!production) await freePort(webPort);
  if (production && !existsSync(path.join(root, 'dist/index.html'))) throw new Error('Execute npm run build antes de npm start.');
  await mkdir(path.join(root, 'data'), { recursive: true });
  const env = { ...process.env, ELO_API_PORT: String(apiPort), ELO_WEB_PORT: String(webPort) };
  if (!env.ELO_ON_DEVICE_BIN) {
    const binary = path.join(root, '.local/elo-on-device');
    try { await access(binary, constants.X_OK); env.ELO_ON_DEVICE_BIN = binary; } catch { /* Optional on-device provider. */ }
  }
  const children = [];
  let stopping = false;
  function stop(code = 0) {
    if (stopping) return;
    stopping = true;
    process.exitCode = code;
    for (const child of children) {
      if (child.exitCode === null) child.kill('SIGTERM');
    }
    setTimeout(() => {
      for (const child of children) if (child.exitCode === null) child.kill('SIGKILL');
    }, 3000).unref();
  }
  process.once('SIGINT', () => stop(0));
  process.once('SIGTERM', () => stop(0));
  const child = (command, args) => {
    const processChild = spawn(command, args, { cwd: root, env, stdio: 'inherit' });
    children.push(processChild);
    processChild.once('error', (error) => { console.error(error.message); stop(1); });
    processChild.once('exit', (code) => { if (!stopping) stop(code || 1); });
    return processChild;
  };
  const args = ['backend/server.py', '--port', String(apiPort), '--db', env.ELO_DB || path.join(root, 'data/elo.sqlite3')];
  args.push(...(production ? ['--dist', path.join(root, 'dist')] : ['--frontend-port', String(webPort)]));
  child(env.PYTHON || (existsSync(path.join(root, '.venv/bin/python3')) ? path.join(root, '.venv/bin/python3') : 'python3'), args);
  for (let attempt = 0; attempt < 100; attempt++) {
    if (stopping) throw new Error('Não foi possível iniciar a API.');
    try {
      const response = await fetch(`http://127.0.0.1:${apiPort}/health`, { signal: AbortSignal.timeout(500) });
      if (response.ok) break;
    } catch { /* Wait for the local child process. */ }
    if (attempt === 99) { stop(1); throw new Error('A API não ficou pronta em 10 segundos.'); }
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  if (!production) child(process.execPath, ['node_modules/vite/bin/vite.js', '--host', '127.0.0.1', '--port', String(webPort), '--strictPort']);
  console.log(`Elo: http://127.0.0.1:${production ? apiPort : webPort}/`);
  if (!env.ELO_ON_DEVICE_BIN && !(env.OPENAI_API_KEY && env.ELO_MODEL)) {
    console.log('IA real não configurada. A síntese local continua disponível. Veja npm run setup:ai.');
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  launch().catch(error => { console.error(error.message); process.exitCode = 1; });
}
