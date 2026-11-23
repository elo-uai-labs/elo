import { spawn } from 'node:child_process';
import { existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
const root = fileURLToPath(new URL('../', import.meta.url));
const localPython = fileURLToPath(new URL('../.venv/bin/python3', import.meta.url));
const child = spawn(process.env.PYTHON || (existsSync(localPython) ? localPython : 'python3'),
  ['-m', 'unittest', 'discover', '-s', 'backend/tests', '-v'], {cwd: root, stdio: 'inherit'});
child.once('error', error => { console.error(error.message); process.exitCode = 1; });
child.once('exit', code => { process.exitCode = code ?? 1; });
