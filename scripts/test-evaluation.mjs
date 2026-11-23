import {spawnSync} from 'node:child_process';
import {existsSync} from 'node:fs';
const result = spawnSync(process.env.PYTHON || (existsSync('.venv/bin/python3') ? '.venv/bin/python3' : 'python3'),
 ['scripts/evaluation_test.py'], {stdio:'inherit'});
process.exitCode = result.status ?? 1;
