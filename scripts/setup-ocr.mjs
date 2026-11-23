import { spawnSync } from 'node:child_process';
import { mkdirSync, renameSync, rmSync, readFileSync, writeFileSync, existsSync, accessSync, constants } from 'node:fs';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('../', import.meta.url));
const modelDirectory = new URL('../.local/tessdata/', import.meta.url);
const manifest = JSON.parse(readFileSync(new URL('../backend/ocr_models.json', import.meta.url), 'utf8'));
const sha = data => createHash('sha256').update(data).digest('hex');
async function installModels() {
  mkdirSync(modelDirectory, { recursive: true });
  for (const [language, expected] of Object.entries(manifest.models)) {
    const target = new URL(`${language}.traineddata`, modelDirectory);
    if (existsSync(target) && sha(readFileSync(target)) === expected.sha256) continue;
    const response = await fetch(`https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/${manifest.commit}/${language}.traineddata`, { signal: AbortSignal.timeout(30000) });
    if (!response.ok) throw new Error(`Falha ao baixar modelo oficial ${language}: HTTP ${response.status}`);
    const reader = response.body.getReader(), chunks = [];
    let size = 0;
    for (;;) {
      const {done, value} = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > expected.bytes) { await reader.cancel(); throw new Error(`Tamanho inesperado do modelo ${language}`); }
      chunks.push(value);
    }
    const data = Buffer.concat(chunks);
    if (data.length !== expected.bytes || sha(data) !== expected.sha256) throw new Error(`Hash ou tamanho inválido do modelo ${language}`);
    const temporary = new URL(`${language}.${process.pid}.tmp`, modelDirectory);
    try { writeFileSync(temporary, data, {mode: 0o600}); renameSync(temporary, target); }
    finally { rmSync(temporary, {force: true}); }
  }
}

try {
  if (process.platform !== 'darwin') throw new Error('Rasterização OCR local requer macOS e SDK PDFKit/ImageIO.');
  const executable = path => { try { accessSync(path, constants.X_OK); return true; } catch { return false; } };
  const candidates = [...(process.env.PATH || '').split(':').filter(Boolean).map(directory => `${directory}/tesseract`),
    '/opt/homebrew/bin/tesseract', '/usr/local/bin/tesseract'];
  const command = Object.hasOwn(process.env, 'ELO_TESSERACT_BIN') ? process.env.ELO_TESSERACT_BIN : candidates.find(executable);
  if (!command) throw new Error('Instale o reconhecedor local: brew install tesseract. Depois repita npm run setup:ocr.');
  const recognizer = spawnSync(command, ['--version'], {cwd: root, encoding: 'utf8'});
  if (recognizer.error || recognizer.status !== 0) throw new Error('Instale o reconhecedor local: brew install tesseract. Depois repita npm run setup:ocr.');
  mkdirSync(new URL('../.local/', import.meta.url), { recursive: true });
  const temporary = `.local/elo-ocr-${process.pid}.tmp`;
  try {
    const result = spawnSync('swiftc', ['-O', 'backend/ocr.swift', '-o', temporary], { cwd: root, stdio: 'inherit' });
    if (result.error || result.status !== 0) throw new Error('Falha ao compilar rasterizador local. Verifique o SDK macOS.');
    await installModels();
    renameSync(new URL(`../${temporary}`, import.meta.url), new URL('../.local/elo-ocr', import.meta.url));
    console.log(`${recognizer.stdout.split('\n')[0]}; rasterizador PDFKit/ImageIO compilado. Modelos oficiais por/eng verificados por SHA-256. OCR de documentos é local, sem rede, e exige revisão humana.`);
  } finally { rmSync(new URL(`../${temporary}`, import.meta.url), { force: true }); }
} catch (error) {
  console.error(error.message);
  process.exitCode = 1;
}
