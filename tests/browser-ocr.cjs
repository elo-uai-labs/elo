'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { execFileSync } = require('node:child_process');

async function choose(control, name) {
  await control.getByRole('combobox').click();
  await control.getByRole('option', { name, exact: true }).click();
}

async function settled(page) {
  await page.waitForFunction(() => document.querySelector('#view')?.getAttribute('aria-busy') === 'false');
  await page.evaluate(async () => {
    await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
    await Promise.all(document.getAnimations().filter(animation => Number.isFinite(animation.effect?.getTiming().iterations))
      .map(animation => animation.finished.catch(() => {})));
  });
}

async function analyze(page, attachment, ocr) {
  const form = page.getByTestId(`${ocr ? 'ocr' : 'analyze'}-${attachment.id}`);
  await form.getByLabel('Responsável pela extração').fill('Analista OCR Demo');
  const pending = page.waitForResponse(response => new URL(response.url()).pathname === '/api/evidence/analyze'
    && response.request().method() === 'POST', { timeout: 120000 });
  await form.getByRole('button', { name: `${ocr ? 'Reconhecer' : 'Extrair'} texto de ${attachment.id}`, exact: true }).click();
  const response = await pending;
  const body = await response.json();
  assert.equal(response.status(), 200, JSON.stringify(body));
  await settled(page);
  return body.document_analyses.find(item => item.attachment_id === attachment.id && (ocr ? item.method === 'ocr' : item.method !== 'ocr'));
}

async function runOCR(browser, pageErrors, baseUrl) {
  const python = process.env.ELO_PYTHON || process.env.PYTHON || (fs.existsSync('.venv/bin/python3') ? '.venv/bin/python3' : 'python3');
  const fixtures = JSON.parse(execFileSync(python, ['backend/tests/ocr_fixtures.py'], { encoding: 'utf8', cwd: path.resolve('.') }));
  const output = path.resolve('output/validation');
  fs.mkdirSync(output, { recursive: true });
  const results = [];
  for (const device of ['desktop', 'mobile']) {
    const page = await browser.newPage({ viewport: device === 'desktop' ? { width: 1440, height: 950 } : { width: 390, height: 844 },
      isMobile: device === 'mobile', hasTouch: device === 'mobile', acceptDownloads: true });
    page.on('pageerror', error => pageErrors.push(error.message));
    try {
      for (const file of [
        { kind: 'png', extension: 'png', mime: 'image/png' },
        { kind: 'jpeg', extension: 'jpg', mime: 'image/jpeg' },
        { kind: 'scan', extension: 'pdf', mime: 'application/pdf' },
        { kind: 'blank', extension: 'png', mime: 'image/png', inconclusive: true }
      ]) {
        const name = `ocr-${device}-${file.kind}.${file.extension}`;
        const buffer = Buffer.from(fixtures[file.kind === 'scan' ? 'pdf' : file.kind], 'base64');
        await page.goto(`${baseUrl}/?case_id=ELO-1042#governanca`);
        await page.getByRole('heading', { name: 'Anexar arquivo ao caso', exact: true }).click();
        const upload = page.getByTestId('upload-ELO-1042-case');
        const chooser = page.waitForEvent('filechooser');
        await upload.getByRole('button', { name: 'Selecionar arquivo de evidência', exact: true }).press('Enter');
        await (await chooser).setFiles({ name, mimeType: file.mime, buffer });
        await upload.getByText(`${name} · ${buffer.length} bytes`, { exact: true }).waitFor();
        await upload.getByLabel('Descrição e relação com o caso').fill('Imagem exclusivamente sintética para avaliar OCR, localização e confirmação humana.');
        await upload.getByLabel('Responsável pelo anexo').fill('Analista OCR Demo');
        await upload.getByLabel('Confirmo que o arquivo contém somente dados fictícios').check();
        await upload.getByRole('button', { name: 'Anexar evidência', exact: true }).click();
        await page.getByRole('link', { name: `Baixar ${name}`, exact: true }).waitFor();
        let state = await (await page.request.get(`${baseUrl}/api/state`)).json();
        const attachment = state.attachments.find(item => item.name === name);
        assert.ok(attachment);
        let literal;
        if (file.kind === 'scan') {
          literal = await analyze(page, attachment, false);
          assert.equal(literal.extraction_status, 'inconclusive');
          assert.equal(literal.text, '');
          await page.getByTestId(`ocr-${attachment.id}`).waitFor();
        }
        const analysis = await analyze(page, attachment, true);
        assert.ok(analysis, 'Análise OCR deve ser identificada separadamente da extração literal.');
        assert.equal(analysis.method, 'ocr');
        assert.ok(analysis.ocr, 'Metadados do motor devem ser preservados.');
        const panel = page.getByTestId(`document-${analysis.id}`);
        const review = page.getByTestId(`document-review-${analysis.id}`);
        await review.waitFor();
        if (file.inconclusive) {
          assert.equal(analysis.extraction_status, 'inconclusive');
          assert.equal(analysis.text.trim(), '');
          assert.equal(await review.locator('p-select-option[value="accepted"]').count(), 0);
          await choose(review.locator('p-select[name=outcome]'), 'Rejeitar texto');
        } else {
          assert.equal(analysis.extraction_status, 'complete');
          assert.match(analysis.text, /CTR-1042/);
          assert.ok(analysis.segments.length > 0);
          for (const segment of analysis.segments) {
            assert.equal(typeof segment.confidence, 'number');
            assert.ok(segment.confidence >= 0 && segment.confidence <= 1);
            assert.ok(segment.bbox, 'Coordenadas do trecho reconhecido preservadas.');
            assert.equal(segment.page, 1);
            assert.equal(typeof segment.location, 'string');
          }
          await panel.getByRole('heading', { name: 'Localizar trechos no original', exact: true }).click();
          await panel.getByText(analysis.segments[0].location, { exact: true }).first().waitFor();
          const downloadEvent = page.waitForEvent('download');
          await panel.getByRole('link', { name: `Baixar documento original · ${attachment.id}`, exact: true }).click();
          const download = await downloadEvent;
          const downloaded = path.join(output, name);
          await download.saveAs(downloaded);
          assert.deepEqual(fs.readFileSync(downloaded), buffer, 'Original da imagem/scan imutável.');
          await choose(review.locator('p-select[name=outcome]'), 'Aceitar texto como fonte');
          const rejected = await page.request.post(`${baseUrl}/api/evidence/review`, { data: {
            analysis_id: analysis.id, revision: analysis.revision, actor: 'Revisora OCR Demo',
            reason: 'Tentativa sem confirmação específica do OCR.', confirmed: true, outcome: 'accepted'
          } });
          assert.equal(rejected.status(), 409, 'Aceitação OCR exige confirmação adicional no backend.');
          const afterAttempt = await (await page.request.get(`${baseUrl}/api/state`)).json();
          assert.equal(afterAttempt.document_analyses.find(item => item.id === analysis.id).status, 'pending');
        }
        await review.getByLabel('Li o texto extraído, conferi o documento e os limites desta extração').check();
        await review.getByLabel('Conferi cada trecho reconhecido com a imagem original').check();
        await review.getByLabel('Responsável pelo registro').fill('Revisora OCR Demo');
        await review.getByLabel('Justificativa do registro').fill(file.inconclusive
          ? 'Imagem sintética branca, sem texto; resultado inconclusivo rejeitado.'
          : 'Texto, coordenadas e fonte sintética original conferidos visualmente.');
        await panel.scrollIntoViewIfNeeded();
        await settled(page);
        assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `${device}/${file.kind}: rolagem horizontal`);
        await page.screenshot({ path: path.join(output, `${device}-ocr-${file.kind}.png`) });
        await review.getByRole('button', { name: 'Registrar revisão do texto', exact: true }).click();
        await panel.locator('.document-status').getByText(file.inconclusive ? 'Texto rejeitado' : 'Texto aceito', { exact: true }).waitFor();
        state = await (await page.request.get(`${baseUrl}/api/state`)).json();
        if (literal) {
          assert.equal(state.document_analyses.find(item => item.id === literal.id).status, 'pending', 'OCR não sobrescreve análise literal inconclusiva.');
          assert.equal(state.document_analyses.filter(item => item.attachment_id === attachment.id).length, 2);
        }
        assert.equal(await page.getByTestId(`ocr-${attachment.id}`).count(), 0, 'OCR não deve ser repetido sobre a mesma fonte.');
        results.push({ device, kind: file.kind, attachment_id: attachment.id, analysis_id: analysis.id,
          literal_analysis_id: literal?.id || null, extraction_status: analysis.extraction_status,
          status: file.inconclusive ? 'rejected' : 'accepted', ocr: analysis.ocr,
          locations: analysis.segments.map(item => ({ location: item.location, page: item.page, bbox: item.bbox, confidence: item.confidence })) });
      }
    } finally { await page.close(); }
  }
  fs.writeFileSync(path.join(output, 'ocr.json'), JSON.stringify(results, null, 2) + '\n');
}

module.exports = { runOCR };
