'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { execFileSync } = require('node:child_process');

async function choose(control, name) {
  await control.getByRole('combobox').click();
  await control.getByRole('option', { name, exact: true }).click();
}

async function runDocumentFormats(browser, pageErrors, baseUrl) {
  // Pure synthetic fixture builders use stdlib only; the server must have its PDF reader installed.
  const fixture = JSON.parse(execFileSync(process.env.ELO_PYTHON || 'python3', ['-c',
    "import sys,json,base64;sys.path.insert(0,'backend/tests');from test_document_formats import digital_pdf,workbook;print(json.dumps({k:base64.b64encode(v).decode() for k,v in {'pdf':digital_pdf(),'scan':digital_pdf(blank=True),'xlsx':workbook()}.items()}))"
  ], { encoding: 'utf8', cwd: path.resolve('.') }));
  const output = path.resolve('output/validation');
  fs.mkdirSync(output, { recursive: true });
  const results = [];
  for (const device of ['desktop', 'mobile']) {
    const page = await browser.newPage({ viewport: device === 'desktop' ? { width: 1440, height: 950 } : { width: 390, height: 844 },
      isMobile: device === 'mobile', hasTouch: device === 'mobile', acceptDownloads: true });
    page.on('pageerror', error => pageErrors.push(error.message));
    try {
      for (const file of [
        { kind: 'pdf', extension: 'pdf', mime: 'application/pdf', location: 'Página 1', text: 'Sintetico CTR-1042' },
        { kind: 'csv', extension: 'csv', mime: 'text/csv', location: 'CSV!A2', text: 'CTR-1042' },
        { kind: 'xlsx', extension: 'xlsx', mime: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', location: 'Origem!C2', text: 'CTR-1042' },
        { kind: 'scan', extension: 'pdf', mime: 'application/pdf', inconclusive: true }
      ]) {
        const name = `fonte-${device}-${file.kind}.${file.extension}`;
        const buffer = file.kind === 'csv' ? Buffer.from('id;descricao\nCTR-1042;Fonte sintetica\n', 'utf8') : Buffer.from(fixture[file.kind], 'base64');
        await page.goto(`${baseUrl}/?case_id=ELO-1042#governanca`);
        await page.getByRole('heading', { name: 'Anexar arquivo ao caso', exact: true }).click();
        const upload = page.getByTestId('upload-ELO-1042-case');
        const chooser = page.waitForEvent('filechooser');
        await upload.getByRole('button', { name: 'Selecionar arquivo de evidência', exact: true }).press('Enter');
        await (await chooser).setFiles({ name, mimeType: file.mime, buffer });
        await upload.getByText(`${name} · ${buffer.length} bytes`, { exact: true }).waitFor();
        await upload.getByLabel('Descrição e relação com o caso').fill('Documento exclusivamente sintético para conferência de página e célula.');
        await upload.getByLabel('Responsável pelo anexo').fill('Analista Formatos Demo');
        await upload.getByLabel('Confirmo que o arquivo contém somente dados fictícios').check();
        await upload.getByRole('button', { name: 'Anexar evidência', exact: true }).click();
        await page.getByRole('link', { name: `Baixar ${name}`, exact: true }).waitFor();
        let state = await (await page.request.get(`${baseUrl}/api/state`)).json();
        const attachment = state.attachments.find(item => item.name === name);
        assert.ok(attachment);
        const extraction = page.getByTestId(`analyze-${attachment.id}`);
        await extraction.getByLabel('Responsável pela extração').fill('Analista Formatos Demo');
        const responsePromise = page.waitForResponse(response => response.url().endsWith('/api/evidence/analyze') && response.request().method() === 'POST');
        await extraction.getByRole('button', { name: `Extrair texto de ${attachment.id}`, exact: true }).click();
        const response = await responsePromise;
        assert.equal(response.status(), 200, `Extração ${file.kind}: ${await response.text()}`);
        state = await response.json();
        const analysis = state.document_analyses.find(item => item.attachment_id === attachment.id);
        const panel = page.getByTestId(`document-${analysis.id}`);
        const review = page.getByTestId(`document-review-${analysis.id}`);
        await review.waitFor();
        if (file.inconclusive) {
          assert.equal(analysis.extraction_status, 'inconclusive');
          assert.equal(analysis.text, '');
          assert.equal(await review.locator('p-select-option[value="accepted"]').count(), 0);
          await panel.getByText(/Extração inconclusiva/).first().waitFor();
          await choose(review.locator('p-select[name=outcome]'), 'Rejeitar texto');
        } else {
          assert.equal(analysis.extraction_status, 'complete');
          await panel.getByTestId('document-text').getByText(new RegExp(file.text)).waitFor();
          await panel.getByRole('heading', { name: 'Localizar trechos no original', exact: true }).click();
          await panel.getByText(file.location, { exact: true }).waitFor();
          assert.ok(analysis.segments.some(segment => segment.location === file.location && segment.text.includes(file.text)));
          const downloadPromise = page.waitForEvent('download');
          await panel.getByRole('link', { name: `Baixar documento original · ${attachment.id}`, exact: true }).click();
          const download = await downloadPromise;
          const downloadPath = path.join(output, name);
          await download.saveAs(downloadPath);
          assert.deepEqual(fs.readFileSync(downloadPath), buffer, 'Fonte original deve preservar bytes');
          await choose(review.locator('p-select[name=outcome]'), 'Aceitar texto como fonte');
        }
        await review.getByLabel('Li o texto extraído, conferi o documento e os limites desta extração').check();
        await review.getByLabel('Responsável pelo registro').fill('Revisora Formatos Demo');
        await review.getByLabel('Justificativa do registro').fill(file.inconclusive ? 'Documento sem camada textual; OCR indisponível, fonte rejeitada.' : 'Trecho e localização conferidos no documento sintético original.');
        await panel.scrollIntoViewIfNeeded();
        assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `${device}/${file.kind}: rolagem horizontal`);
        await page.screenshot({ path: path.join(output, `${device}-document-${file.kind}.png`) });
        await review.getByRole('button', { name: 'Registrar revisão do texto', exact: true }).click();
        await panel.locator('.document-status').getByText(file.inconclusive ? 'Texto rejeitado' : 'Texto aceito', { exact: true }).waitFor();
        results.push({ device, kind: file.kind, attachment_id: attachment.id, analysis_id: analysis.id,
          extraction_status: analysis.extraction_status, location: file.location || null, status: file.inconclusive ? 'rejected' : 'accepted' });
      }
    } finally { await page.close(); }
  }
  fs.writeFileSync(path.join(output, 'document-formats.json'), JSON.stringify(results, null, 2) + '\n');
}

module.exports = { runDocumentFormats };
