// Paid opt-in is checked before .env access. Credentials remain in environment.
import {existsSync} from 'node:fs';
import {spawnSync} from 'node:child_process';
import path from 'node:path';
const args=process.argv.slice(2);
if(!args.includes('--help') && (!args.includes('--real') || !args.includes('--allow-paid'))) {
  console.error('Required: --real --allow-paid --output NEW_DIRECTORY'); process.exit(2);
}
const root=path.resolve(import.meta.dirname,'..'); process.chdir(root);
if(!args.includes('--help') && existsSync('.env'))process.loadEnvFile('.env');
const result=spawnSync(process.env.PYTHON || (existsSync('.venv/bin/python3')?'.venv/bin/python3':'python3'),
 ['scripts/independent-ai-evaluation.py',...args],{cwd:root,env:process.env,stdio:'inherit'});
process.exitCode=result.status??1;
