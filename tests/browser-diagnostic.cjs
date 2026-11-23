'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

async function choose(control, label) {
  await control.getByRole('combobox').click();
  await control.getByRole('option', { name: label, exact: true }).click();
}

async function settle(page) {
  await page.evaluate(async () => {
    await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
    await Promise.all(document.getAnimations().filter((animation) => Number.isFinite(animation.effect?.getTiming().iterations))
      .map((animation) => animation.finished.catch(() => {})));
  });
}

async function submit(page, form, name, endpoint) {
  const pending = page.waitForResponse((response) => new URL(response.url()).pathname === `/api/${endpoint}` && response.request().method() === 'POST');
  await form.getByRole('button', { name, exact: true }).click();
  const response = await pending;
  const body = await response.json();
  assert.ok(response.ok(), `${endpoint}: ${JSON.stringify(body)}`);
  await page.waitForFunction(() => document.querySelector('#view')?.getAttribute('aria-busy') === 'false');
  return body;
}

function xlsxBytes(rows) {
  const code = `import io,json,sys,zipfile
from xml.sax.saxutils import escape
rows=json.loads(sys.argv[1])
sheet='<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'
for ri,row in enumerate(rows,1):
 sheet += '<row r="%s">'%ri
 for ci,value in enumerate(row):
  sheet += '<c r="%s%s" t="inlineStr"><is><t>%s</t></is></c>'%(chr(65+ci),ri,escape(value))
 sheet += '</row>'
sheet += '</sheetData></worksheet>'
b=io.BytesIO()
with zipfile.ZipFile(b,'w',zipfile.ZIP_DEFLATED) as z:
 z.writestr('[Content_Types].xml','<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>')
 z.writestr('_rels/.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
 z.writestr('xl/workbook.xml','<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Contratos" sheetId="1" r:id="rId1"/></sheets></workbook>')
 z.writestr('xl/_rels/workbook.xml.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>')
 z.writestr('xl/worksheets/sheet1.xml',sheet)
sys.stdout.buffer.write(b.getvalue())`;
  return require('node:child_process').execFileSync('python3', ['-c', code, JSON.stringify(rows)]);
}

async function runDiagnostic(browser, pageErrors, baseUrl) {
  const output = path.resolve('output/validation');
  fs.mkdirSync(output, { recursive: true });
  const evidence = { scope: 'Dados sintéticos; banco temporário do teste canônico.', runs: [] };
  for (const mode of ['desktop', 'mobile']) {
    const page = await browser.newPage(mode === 'desktop'
      ? { viewport: { width: 1440, height: 950 }, locale: 'pt-BR' }
      : { viewport: { width: 390, height: 844 }, locale: 'pt-BR', isMobile: true, hasTouch: true });
    page.on('pageerror', (error) => pageErrors.push(error.message));
    const snapshot = async () => (await page.request.get(`${baseUrl}/api/state`)).json();
    const run = { viewport: mode, imports: [], errors: ['XLSX inválido', 'Mapeamento obrigatório ausente'] };
    try {
      await page.goto(`${baseUrl}/?case_id=ELO-1042#inteligencia`);
      await page.getByRole('heading', { name: 'Central de inteligência', exact: true }).waitFor();
      let before = await snapshot();
      const rule = before.rules.find((item) => item.id === 'contact-code-match');
      if (!rule.configuration.enabled) {
        await page.getByRole('heading', { name: `Configurar regra · ${rule.name}`, exact: true }).click();
        const config = page.getByTestId('rule-config-contact-code-match');
        await config.getByLabel('Regra habilitada').check();
        await config.getByLabel('Responsável pelo registro').fill('Analista Diagnóstico');
        await config.getByLabel('Justificativa do registro').fill('Reativar análise sintética para validar os lotes positivo e negativo.');
        await submit(page, config, 'Salvar parâmetros da regra', 'rule/config');
      }
      before = await snapshot();
      if (!before.dataset.suppliers.some((item) => item.id !== 'FOR-031' && item.contact_code === 'FICT-801')) {
        await page.getByRole('heading', { name: 'Importar base sintética', exact: true }).click();
        const setup = page.getByTestId('import-form');
        await setup.getByLabel('Base sintética em JSON').fill(JSON.stringify({ employees: [], contracts: [],
          suppliers: [{ id: 'FOR-DIAG-SHARED', name: 'Fornecedor fictício diagnóstico', contact_code: 'FICT-801' }] }));
        await setup.getByLabel('Responsável pela importação').fill('Preparador Diagnóstico');
        await choose(page.locator('#import-synthetic'), 'Confirmo que todos os dados são fictícios');
        await submit(page, setup, 'Importar base', 'import');
      }
      for (const scenario of [{ positive: true, format: 'csv', suffix: 'POS' }, { positive: false, format: 'csv', suffix: 'NEG' }, { positive: false, format: 'xlsx', suffix: 'XLSX' }]) {
        const { positive, format, suffix } = scenario;
        const id = `CTR-DIAG-${mode.toUpperCase()}-${suffix}`;
        before = await snapshot();
        await page.getByRole('heading', { name: 'Importar CSV ou XLSX', exact: true }).click();
        let form = page.getByTestId('tabular-preview');
        if (positive) {
          await page.locator('#file-tabular').setInputFiles({ name: 'invalido.xlsx', mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', buffer: Buffer.from('arquivo inválido') });
          await choose(page.locator('#import-table'), 'Contratos');
          await form.getByLabel('Confirmo que a base contém somente dados fictícios').check();
          const failedResponse = page.waitForResponse((response) => new URL(response.url()).pathname === '/api/import/preview');
          await form.getByRole('button', { name: 'Validar arquivo e mapeamento', exact: true }).click();
          const rejected = await failedResponse;
          assert.equal(rejected.status(), 422);
          await page.getByText(/Arquivo XLSX inválido/).waitFor();
          assert.deepEqual((await snapshot()).dataset, before.dataset);
        }
        const header = positive ? 'identifier' : 'id';
        const csv = `${header},supplier_id,approver_id,title\n${id},${positive ? 'FOR-031,EMP-014' : 'FOR-042,EMP-027'},Contrato sintético diagnóstico ${mode}\n`;
        await page.locator('#file-tabular').setInputFiles(format === 'csv'
          ? { name: `${positive ? 'positivo' : 'negativo'}-${mode}.csv`, mimeType: 'text/csv', buffer: Buffer.from(csv) }
          : { name: `contratos-${mode}.xlsx`, mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            buffer: xlsxBytes([['id', 'supplier_id', 'approver_id', 'title'], [id, 'FOR-042', 'EMP-027', 'Contrato fictício planilha']]) });
        await choose(page.locator('#import-table'), 'Contratos');
        form = page.getByTestId('tabular-preview');
        await form.getByLabel('Confirmo que a base contém somente dados fictícios').check();
        let preview = await submit(page, form, 'Validar arquivo e mapeamento', 'import/preview');
        if (positive) {
          assert.equal(preview.ready, false);
          await page.getByTestId('import-preview-result').getByText('Corrigir mapeamento ou registros', { exact: true }).waitFor();
          assert.equal(await page.getByTestId('tabular-confirm').count(), 0);
          await choose(page.locator('#map-id'), 'identifier');
          form = page.getByTestId('tabular-preview');
          await form.getByLabel('Confirmo que a base contém somente dados fictícios').check();
          preview = await submit(page, form, 'Validar arquivo e mapeamento', 'import/preview');
        }
        assert.equal(preview.ready, true);
        assert.deepEqual(preview.counts, { records: 1, valid: 1, errors: 0 });
        assert.deepEqual((await snapshot()).dataset, before.dataset, 'Prévia não grava dados.');
        await page.getByTestId('import-preview-result').getByText('Pronto para confirmar', { exact: true }).waitFor();
        if (positive) {
          // Editing a ready preview must invalidate its saved request, even before another validation.
          await choose(page.locator('#map-title'), 'identifier');
          assert.equal(await page.getByTestId('tabular-confirm').count(), 0,
            'Alterar mapeamento remove confirmação da configuração anterior.');
          await page.getByTestId('import-preview-result').getByText('Configuração alterada: valide novamente', { exact: true }).waitFor();
          assert.deepEqual((await snapshot()).dataset, before.dataset, 'Editar prévia não grava dados.');
          await choose(page.locator('#map-title'), 'title');
          assert.equal(await page.getByTestId('tabular-confirm').count(), 0,
            'Restaurar seleção também exige nova validação.');
          form = page.getByTestId('tabular-preview');
          await form.getByLabel('Confirmo que a base contém somente dados fictícios').check();
          preview = await submit(page, form, 'Validar arquivo e mapeamento', 'import/preview');
          assert.equal(preview.ready, true);
          await page.getByTestId('tabular-confirm').waitFor();
          run.preview_edit_invalidated = true;
        }
        await page.getByTestId('import-preview-result').scrollIntoViewIfNeeded();
        await settle(page);
        assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'Prévia sem rolagem horizontal.');
        if (positive) await page.screenshot({ path: path.join(output, `${mode}-diagnostic-import.png`) });
        const confirmation = page.getByTestId('tabular-confirm');
        await confirmation.getByLabel('Responsável pela importação').fill('Analista Diagnóstico');
        await confirmation.getByLabel('Conferi a prévia e confirmo a importação').check();
        await submit(page, confirmation, 'Confirmar importação do arquivo', 'import/file');
        const imported = await snapshot();
        assert.equal(imported.dataset.contracts.length, before.dataset.contracts.length + 1);
        assert.deepEqual(imported.cases, before.cases, 'Importação ainda não executa detecção.');
        const detected = await submit(page, page.locator('form[data-endpoint="detect"]').filter({ has: page.getByTestId('detect') }), 'Executar análise', 'detect');
        const expectedId = `ELO-DIAG-${mode.toUpperCase()}-${suffix}`;
        assert.equal(detected.cases.some((item) => item.id === expectedId), positive);
        if (!positive) {
          assert.deepEqual(detected.cases, imported.cases);
          await page.getByText('Análise concluída sem novos indícios', { exact: true }).waitFor();
        }
        run.imports.push({ format, contract_id: id, expected_signal: positive, case_id: positive ? expectedId : null,
          preview: preview.counts, total_contracts: imported.dataset.contracts.length, total_signals: detected.cases.length });
      }
      await submit(page, page.locator('form[data-endpoint="detect"]').filter({ has: page.getByTestId('detect-suppliers') }), 'Analisar fornecedores relacionados', 'detect');
      const analytical = await (await page.request.get(`${baseUrl}/api/insights`)).json();
      const contract = `CTR-DIAG-${mode.toUpperCase()}-POS`;
      const group = analytical.correlation.groups.find((item) => item.contract_id === contract);
      assert.ok(group, 'Contrato positivo presente na correlação.');
      assert.equal(group.distinct_rule_count, 2, 'Duas regras sobre um contrato são mostradas em conjunto.');
      assert.equal(group.signal_count, 2);
      assert.equal(new Set(group.case_ids).size, 2);
      assert.ok(!analytical.correlation.groups.some((item) => item.contract_id === `CTR-DIAG-${mode.toUpperCase()}-NEG`));
      await page.getByTestId(`correlation-${contract}`).getByText(contract, { exact: false }).first().waitFor();
      await page.getByTestId(`correlation-${contract}`).scrollIntoViewIfNeeded();
      await settle(page);
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
      await page.screenshot({ path: path.join(output, `${mode}-diagnostic-groups.png`) });
      const groupPanel = page.getByTestId(`correlation-${contract}`);
      const selectedResponse = page.waitForResponse(response => new URL(response.url()).pathname === '/api/state' && new URL(response.url()).searchParams.get('case_id') === group.signals[0].case_id);
      await groupPanel.getByRole('button', {name: `Analisar ${group.signals[0].case_id}`, exact: true}).click();
      assert.equal((await (await selectedResponse).json()).case.id, group.signals[0].case_id);
      await page.waitForFunction(() => document.querySelector('#view').getAttribute('aria-busy') === 'false');
      run.correlation = group;
      await page.goto(`${baseUrl}/#visao`);
      await page.getByTestId('capabilities').getByRole('heading').click();
      await page.getByTestId('capabilities').getByText('Funcional local', { exact: true }).waitFor();
      await page.getByTestId('capabilities').getByText('Experimental', { exact: true }).waitFor();
      await page.getByTestId('capabilities').getByText('Planejado / depende da CAIXA', { exact: true }).waitFor();
      evidence.runs.push(run);
    } finally { await page.close(); }
  }
  fs.writeFileSync(path.join(output, 'diagnostic.json'), JSON.stringify(evidence, null, 2));
}

module.exports = { runDiagnostic };
