// No paid requests without both explicit flags. Never print credentials.
import {existsSync} from 'node:fs';
import {spawnSync} from 'node:child_process';
import path from 'node:path';
const root = path.resolve(import.meta.dirname, '..');
process.chdir(root);
const args = process.argv.slice(2);
const smoke = args.includes('--smoke');
if (!smoke && !(args.includes('--real') && args.includes('--allow-paid'))) {
  console.error('Use --smoke (sem API) ou --real --allow-paid (até duas chamadas OpenAI).');
  process.exit(2);
}
if (!smoke && existsSync('.env')) process.loadEnvFile('.env');
const result = spawnSync(process.env.PYTHON || (existsSync('.venv/bin/python3') ? '.venv/bin/python3' : 'python3'),
  ['scripts/trl-real-operation.py', ...args], {cwd:root, env:process.env, stdio:'inherit'});
process.exitCode = result.status ?? 1;
