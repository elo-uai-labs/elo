import { spawnSync } from 'node:child_process';
import { mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

if (process.platform !== 'darwin') {
  console.error('IA Apple requer macOS com Apple Intelligence e SDK Foundation Models. Alternativa: configure OPENAI_API_KEY e ELO_MODEL no ambiente.');
  process.exitCode = 1;
} else {
  const root = fileURLToPath(new URL('../', import.meta.url));
  mkdirSync(new URL('../.local/', import.meta.url), { recursive: true });
  const result = spawnSync('swiftc', ['-parse-as-library', 'backend/on_device.swift', '-o', '.local/elo-on-device'], { cwd: root, stdio: 'inherit' });
  if (result.error) console.error(result.error.message);
  process.exitCode = result.status ?? 1;
  if (process.exitCode === 0) console.log('Executável Apple compilado em .local/elo-on-device. Reinicie npm run dev ou npm start. A disponibilidade do modelo será validada na geração do dossiê.');
}
