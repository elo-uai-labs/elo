import { launch } from './dev.mjs';

launch({ production: true }).catch(error => { console.error(error.message); process.exitCode = 1; });
