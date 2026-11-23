// Explicit real-call opt-in; .env stays in process environment and is never printed.
import {existsSync} from 'node:fs';
import {spawnSync} from 'node:child_process';
import path from 'node:path';
const root=path.resolve(import.meta.dirname,'..');process.chdir(root);
if(existsSync('.env'))process.loadEnvFile('.env');
const result=spawnSync(process.env.PYTHON || (existsSync('.venv/bin/python3') ? '.venv/bin/python3' : 'python3'),
 ['scripts/trl-evaluation-regression.py',...process.argv.slice(2)],{cwd:root,env:process.env,stdio:'inherit'});
process.exitCode=result.status ?? 1;
