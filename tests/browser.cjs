'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const output = path.resolve('output/validation');
fs.mkdirSync(output, { recursive: true });

const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const baseUrl = process.env.ELO_URL || 'http://127.0.0.1:8000';
const reason = 'Registrar a fragilidade cadastral e verificar a origem com a área responsável.';
const aiMode = process.env.ELO_TEST_DOSSIER || 'local';

async function choose(control, label) {
  await control.getByRole('combobox').click();
  await control.getByRole('option', { name: label, exact: true }).click();
}

function input(page, selector) {
  return page.locator(selector).locator('input, textarea');
}

async function verifyDesignSystem(page, selectors) {
  await page.waitForFunction((requiredSelectors) => requiredSelectors.every((selector) => {
    const elements = Array.from(document.querySelectorAll(selector));
    return elements.length > 0 && elements.every((element) => element.classList.contains('hydrated'));
  }), selectors);
  const nativeControls = await page.evaluate(() => Array.from(document.querySelectorAll(
    'a[href], button, select, textarea, input:not([type=hidden]), ul, ol, h1, h2, h3, details'
  )).filter((element) => !element.matches('p-tabs-bar > a')).map((element) => element.outerHTML));
  assert.deepEqual(nativeControls, [], 'A interface deve usar o componente oficial quando há equivalente no PDS.');
}

async function verifyTypography(page, selector, shadowSelector) {
  await page.evaluate(() => document.fonts.ready);
  const result = await page.locator(selector).first().evaluate((host, query) => {
    const inner = host.shadowRoot.querySelector(query);
    const style = getComputedStyle(inner);
    const theme = getComputedStyle(document.documentElement);
    const weight = host.getAttribute('weight') || 'normal';
    const result = {
      family: style.fontFamily,
      officialFamily: theme.getPropertyValue('--p-font-porsche-next'),
      weight: style.fontWeight,
      officialWeight: theme.getPropertyValue(`--p-font-weight-${weight}`).trim(),
    };
    if (host.matches('p-heading, p-text')) {
      const scale = host.getAttribute('size') || (host.matches('p-heading') ? '2xl' : 'sm');
      const sample = document.createElement('span');
      sample.style.cssText = `position:fixed;visibility:hidden;font-family:var(--p-font-porsche-next);font-size:var(--p-typescale-${scale});font-weight:var(--p-font-weight-${weight});line-height:var(--p-leading-normal)`;
      document.body.append(sample);
      const expected = getComputedStyle(sample);
      Object.assign(result, { size: parseFloat(style.fontSize), officialSize: parseFloat(expected.fontSize),
        line: parseFloat(style.lineHeight), officialLine: parseFloat(expected.lineHeight) });
      sample.remove();
    }
    return result;
  }, shadowSelector);
  const normalize = (family) => family.replace(/[\s"']/g, '').toLowerCase();
  assert.match(normalize(result.officialFamily), /^porschenext,arialnarrow,arial,/);
  assert.equal(normalize(result.family), normalize(result.officialFamily), `Família tipográfica do PDS em ${selector}`);
  assert.equal(result.weight, result.officialWeight, `Peso tipográfico do PDS em ${selector}`);
  if (result.size !== undefined) {
    assert.ok(Math.abs(result.size - result.officialSize) < 0.05, `Escala tipográfica do PDS em ${selector}`);
    assert.ok(Math.abs(result.line - result.officialLine) < 0.05, `Entrelinha do PDS em ${selector}`);
  }
  // Computed font-family alone also passes when the browser silently falls back.
  const session = await page.context().newCDPSession(page);
  try {
    await session.send('DOM.enable');
    await session.send('CSS.enable');
    const { root } = await session.send('DOM.getDocument', { depth: -1, pierce: true });
    const { nodeId: hostId } = await session.send('DOM.querySelector', { nodeId: root.nodeId, selector });
    const { node } = await session.send('DOM.describeNode', { nodeId: hostId, depth: 1, pierce: true });
    const { nodeId } = await session.send('DOM.querySelector', { nodeId: node.shadowRoots[0].nodeId, selector: shadowSelector });
    const { fonts } = await session.send('CSS.getPlatformFontsForNode', { nodeId });
    const rendered = fonts.filter((font) => font.glyphCount > 0);
    // The official WOFF2 files can expose an empty internal family name in CDP.
    // Verify both the loaded CSS family and real webfont glyphs, never fallback glyphs.
    const fontFaces = await page.evaluate(() => [...document.fonts]
      .filter((font) => font.status === 'loaded').map((font) => ({ family: font.family, weight: font.weight })));
    assert.ok(fontFaces.some((font) => /Porsche Next/.test(font.family) && font.weight === result.weight), `Fonte oficial carregada para ${selector}`);
    assert.ok(rendered.length > 0 && rendered.every((font) => font.isCustomFont), `Porsche Next precisa ser desenhada sem fallback em ${selector}: ${JSON.stringify(rendered)}`);
    fs.appendFileSync(path.join(output, 'typography.jsonl'), JSON.stringify({ selector, ...result, rendered, fontFaces }) + '\n');
  } finally {
    await session.detach();
  }
}

async function decideImpact(page, kind, outcome, justification) {
  const prefix = `impact-${kind}`;
  await choose(page.locator(`#${prefix}-outcome`), outcome === 'approved' ? 'Aprovar' : 'Recusar');
  await input(page, `#${prefix}-actor`).fill('Rita Demo');
  await input(page, `#${prefix}-reason`).fill(justification);
  const proposal = page.getByTestId(prefix);
  await proposal.getByRole('button', { name: 'Registrar avaliação' }).click();
  await proposal.getByText(outcome === 'approved' ? 'Aprovado' : 'Recusado', { exact: true }).waitFor();
}

async function runDesktop(browser, pageErrors) {
  const page = await browser.newPage({ viewport: { width: 1440, height: 950 }, locale: 'pt-BR' });
  page.on('pageerror', (error) => pageErrors.push(error.message));
  await page.goto(baseUrl);

  await page.getByRole('heading', { name: 'Visão geral', exact: true }).waitFor();
  await verifyDesignSystem(page, ['p-tabs-bar', 'p-heading', 'p-link', 'p-link-pure', 'p-tag', 'p-text-list', 'p-text-list-item']);
  await verifyTypography(page, 'p-heading[tag=h1]', 'h1');
  await verifyTypography(page, 'main p-text.hydrated', 'p, span');
  await verifyTypography(page, '.metric-value.hydrated', 'p, span');
  await page.screenshot({ path: path.join(output, 'desktop-visao.png'), fullPage: true });
  await page.keyboard.press('Tab');
  await page.getByRole('link', { name: 'Ir para o conteúdo' }).press('Enter');
  assert.equal(await page.evaluate(() => document.activeElement.id), 'conteudo');
  await page.getByTestId('open-intelligence').click();
  await page.getByTestId('detect').click();
  await page.getByTestId('evidence-list').getByRole('listitem').first().waitFor();
  await page.getByRole('link', { name: 'Ir para o conteúdo' }).press('Enter');
  assert.equal(new URL(page.url()).hash, '#inteligencia');
  assert.equal(await page.evaluate(() => document.activeElement.id), 'conteudo');
  await choose(page.locator('#dossier-mode'), aiMode === 'real' ? 'IA real (requer configuração)' : 'Síntese local');
  // A transient provider failure must remain visible and allow another attempt.
  await page.route('**/api/dossier', (route) => route.fulfill({
    status: 503, contentType: 'application/json', body: JSON.stringify({ error: 'Modelo temporariamente indisponível.' }),
  }), { times: 1 });
  await page.getByTestId('generate-dossier').click();
  await page.getByText('Modelo temporariamente indisponível.', { exact: true }).waitFor();
  assert.equal((await (await page.request.get(`${baseUrl}/api/state`)).json()).case.dossier, null);
  const dossierResponse = page.waitForResponse((response) => response.url().endsWith('/api/dossier'), { timeout: 55000 });
  await page.getByTestId('generate-dossier').click();
  const completedDossier = await dossierResponse;
  if (!completedDossier.ok()) {
    throw new Error(`Dossiê retornou HTTP ${completedDossier.status()}: ${await completedDossier.text()}`);
  }
  await page.getByTestId('dossier').waitFor();
  await page.getByText(aiMode === 'real' ? /^IA real · / : 'Síntese local baseada nas evidências').waitFor();
  await verifyDesignSystem(page, ['p-select', 'p-select-option', 'p-input-text', 'p-textarea', 'p-button', 'p-inline-notification']);
  await verifyTypography(page, '#decision-actor', 'label');
  await page.screenshot({ path: path.join(output, 'desktop-inteligencia.png'), fullPage: true });

  await choose(page.locator('#decision-outcome'), 'Registrar fragilidade');
  await input(page, '#decision-actor').fill('Lia Demo');
  await input(page, '#decision-reason').fill(reason);
  const incompleteDecision = await page.getByTestId('decision-form').evaluate((form) => Object.fromEntries(new FormData(form)));
  assert.ok(!incompleteDecision.review);
  const rejected = await page.request.post(new URL('/api/decision', baseUrl).href, { data: incompleteDecision });
  assert.equal(rejected.status(), 422);
  await choose(page.locator('#decision-review'), 'Ajustar');
  await page.getByRole('button', { name: 'Registrar decisão' }).click();
  await page.getByTestId('case-decision').getByText('Ajustou a sugestão', { exact: true }).waitFor();
  await page.getByRole('link', { name: 'Avaliar impacto em risco e maturidade' }).click();
  await page.getByTestId('impact-risk').getByRole('link', { name: 'Caso ELO-1042' }).waitFor();
  await page.getByTestId('impact-risk').getByText('Moderada → Alta', { exact: true }).waitFor();
  await verifyDesignSystem(page, ['p-text-list', 'p-link-pure', 'p-tag', 'p-select', 'p-button']);
  await decideImpact(page, 'risk', 'approved', 'Reavaliar a exposição ao vínculo relatado.');
  await decideImpact(page, 'maturity', 'rejected', 'A amostra ainda não permite revisar a dimensão.');
  await page.screenshot({ path: path.join(output, 'desktop-impactos.png'), fullPage: true });

  await page.getByRole('link', { name: 'Abrir plano e auditoria' }).click();
  await input(page, '#action-title').fill('Revisar a rotina de declaração');
  await input(page, '#action-owner').fill('Marco Demo');
  await input(page, '#action-due').fill('2027-01-15');
  await input(page, '#action-actor').fill('Lia Demo');
  await page.getByRole('button', { name: 'Criar plano de ação' }).click();
  const action = page.getByTestId('action-item');
  await action.getByText('Revisar a rotina de declaração', { exact: true }).waitFor();
  await verifyDesignSystem(page, ['p-input-date', 'p-accordion', 'p-text-list', 'p-tag', 'p-button']);
  await action.getByText('Atualizar andamento', { exact: true }).click();
  await choose(action.locator('p-select[name=status]'), 'Em andamento');
  await action.getByLabel('Quem está registrando').fill('Marco Demo');
  await action.getByRole('button', { name: 'Salvar andamento' }).click();
  await action.locator('.badge').getByText('Em andamento', { exact: true }).waitFor();
  await action.getByText('Atualizar andamento', { exact: true }).click();
  await choose(action.locator('p-select[name=status]'), 'Concluído');
  await action.getByLabel('Quem está registrando').fill('Marco Demo');
  await action.getByLabel('Evidência de execução').fill('Ata sintética DEMO-01.');
  await action.getByRole('button', { name: 'Salvar andamento' }).click();
  await action.locator('.badge').getByText('Concluído', { exact: true }).waitFor();
  await action.getByText('Evidência: Ata sintética DEMO-01.', { exact: true }).waitFor();

  const supervision = page.getByTestId('supervision');
  await supervision.getByText(aiMode === 'real' ? 'Sugestão da IA' : 'Síntese local revisada', { exact: true }).waitFor();
  await supervision.getByText('Ajustou a sugestão', { exact: true }).waitFor();
  await supervision.getByText(reason, { exact: true }).waitFor();
  await page.getByText('Integridade verificada', { exact: true }).waitFor();
  assert.ok(await page.getByTestId('audit-event').count() >= 7);

  await page.reload();
  await action.locator('.badge').getByText('Concluído', { exact: true }).waitFor();
  await page.screenshot({ path: path.join(output, 'desktop-governanca.png'), fullPage: true });
  await page.goto(`${baseUrl}/#visao`);
  await page.getByRole('heading', { name: 'Visão geral', exact: true }).waitFor();
  const values = await page.locator('.metric-value').allTextContents();
  assert.deepEqual(values, ['0', 'Alta', '0', '0', 'Intermediária']);
  await page.close();
}

async function runMobile(browser, pageErrors) {
  const page = await browser.newPage({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
  page.on('pageerror', (error) => pageErrors.push(error.message));
  await page.goto(baseUrl);
  const navigation = page.getByRole('navigation', { name: 'Módulos do Elo' });
  await navigation.locator('p-tabs-bar.hydrated').waitFor();
  const screens = [
    ['Visão geral', 'Visão geral'],
    ['Inteligência', 'Central de inteligência'],
    ['Risco e maturidade', 'Risco e maturidade'],
    ['Plano e auditoria', 'Plano de ação e auditoria'],
  ];
  for (const [index, [item, heading]] of screens.entries()) {
    const link = navigation.locator('a').filter({ hasText: item });
    await link.tap();
    await page.getByRole('heading', { name: heading, exact: true }).waitFor();
    await link.and(navigation.locator('a[aria-current="true"]')).waitFor();
    assert.equal(await navigation.locator('p-tabs-bar').evaluate((tabBar) => tabBar.activeTabIndex), index);
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), `${heading} tem rolagem horizontal`);
    await verifyTypography(page, 'p-heading[tag=h1]', 'h1');
    await page.screenshot({ path: path.join(output, `mobile-${index}.png`), fullPage: true });
  }
  await page.getByTestId('supervision').getByText(reason, { exact: true }).waitFor();
  await page.close();
}

async function runExpanded(browser, pageErrors) {
  const page = await browser.newPage({ viewport: { width: 1440, height: 950 }, locale: 'pt-BR', acceptDownloads: true });
  page.on('pageerror', (error) => pageErrors.push(error.message));
  const snapshot = async () => (await page.request.get(`${baseUrl}/api/state`)).json();
  const original = await snapshot();
  const originalCase = structuredClone(original.case);
  await page.goto(`${baseUrl}/#inteligencia`);
  await page.getByRole('heading', { name: 'Central de inteligência', exact: true }).waitFor();
  await page.getByRole('heading', { name: 'Importar base sintética', exact: true }).click();
  await input(page, '#import-actor').fill('Importador Demo');
  await choose(page.locator('#import-synthetic'), 'Confirmo que todos os dados são fictícios');
  await input(page, '#import-dataset').fill('{ inválido');
  await page.getByRole('button', { name: 'Importar base', exact: true }).click();
  await page.getByText('A base deve conter um JSON válido. Revise o conteúdo antes de importar.', { exact: true }).waitFor();
  assert.deepEqual((await snapshot()).dataset, original.dataset);
  assert.equal(await page.getByTestId('detect').getByRole('button').isDisabled(), true);
  const batch = {
    employees: [{ id: 'EMP-200', name: 'Pessoa fictícia <teste>', role: 'Aprovação', contact_code: 'FICT-200' }],
    suppliers: [{ id: 'FOR-200', name: 'Empresa fictícia 200', contact_code: 'FICT-200' }],
    contracts: [
      { id: 'CTR-2001', title: 'Contrato sintético 2001', approver_id: 'EMP-200', supplier_id: 'FOR-200' },
      { id: 'CTR-2002', title: 'Contrato sintético 2002', approver_id: 'EMP-200', supplier_id: 'FOR-200' },
    ],
  };
  await input(page, '#import-dataset').fill(JSON.stringify(batch));
  await page.getByRole('button', { name: 'Importar base', exact: true }).click();
  await page.getByText('Registro atualizado.', { exact: true }).waitFor();
  assert.equal((await snapshot()).dataset.contracts.length, original.dataset.contracts.length + 2);
  await page.getByTestId('detect').click();
  await page.getByText('3 indício(s) detectado(s). 0 contrato(s) ainda não analisado(s).', { exact: true }).waitFor();
  assert.equal((await snapshot()).cases.length, 3);
  assert.deepEqual((await snapshot()).cases[0], originalCase);
  await choose(page.locator('#selected-case'), 'ELO-2002 · Aguardando análise');
  await page.getByRole('button', { name: 'Abrir caso selecionado', exact: true }).click();
  await page.getByRole('heading', { name: 'Possível conflito de interesses · ELO-2002', exact: true }).waitFor();
  await page.getByRole('heading', { name: 'Abrir registro EMP-200', exact: true }).click();
  await page.getByTestId('evidence-list').getByText(/"name": "Pessoa fictícia <teste>"/).waitFor();
  assert.equal(await page.locator('teste').count(), 0, 'Registros precisam ser escapados');
  await choose(page.locator('#dossier-mode'), 'Síntese local');
  await page.getByTestId('generate-dossier').click();
  await page.getByTestId('dossier').waitFor();
  await choose(page.locator('#decision-review'), 'Rejeitar');
  await choose(page.locator('#decision-outcome'), 'Descartar');
  await input(page, '#decision-actor').fill('Analista Demo 2');
  await input(page, '#decision-reason').fill('Código sintético compartilhado por coincidência; indício descartado após revisão.');
  await page.getByRole('button', { name: 'Registrar decisão', exact: true }).click();
  await page.getByTestId('case-decision').getByText('Rejeitou a sugestão', { exact: true }).waitFor();
  await page.reload();
  await page.getByTestId('case-decision').getByText('Rejeitou a sugestão', { exact: true }).waitFor();
  assert.equal(new URL(page.url()).searchParams.get('case_id'), 'ELO-2002');
  const afterDecision = await snapshot();
  assert.deepEqual(afterDecision.cases[0], originalCase);
  assert.equal(afterDecision.cases.find((item) => item.id === 'ELO-2001').decision, null);
  assert.equal(afterDecision.cases.find((item) => item.id === 'ELO-2002').decision.outcome, 'discard');

  // A new nonmatching batch is processed and audited without inventing an alert.
  await page.getByRole('heading', { name: 'Importar base sintética', exact: true }).click();
  await input(page, '#import-actor').fill('Importador Demo');
  await choose(page.locator('#import-synthetic'), 'Confirmo que todos os dados são fictícios');
  await input(page, '#import-dataset').fill(JSON.stringify({ employees: [], suppliers: [], contracts: [
    { id: 'CTR-2003', title: 'Contrato sintético sem vínculo', approver_id: 'EMP-200', supplier_id: 'FOR-042' },
  ] }));
  await page.getByRole('button', { name: 'Importar base', exact: true }).click();
  await page.getByText('Registro atualizado.', { exact: true }).waitFor();
  await page.getByTestId('detect').click();
  await page.getByText('Análise concluída sem novos indícios', { exact: true }).waitFor();
  const afterNoMatch = await snapshot();
  assert.equal(afterNoMatch.cases.length, 3);
  assert.deepEqual(afterNoMatch.audit.at(-1).details.case_ids, []);
  assert.deepEqual(afterNoMatch.audit.at(-1).details.contracts_analyzed, ['CTR-2003']);
  await verifyDesignSystem(page, ['p-select', 'p-textarea', 'p-input-text', 'p-accordion', 'p-button']);
  await page.screenshot({ path: path.join(output, 'desktop-multiple-cases.png'), fullPage: true });
  await page.goto(`${baseUrl}/#visao`);
  await page.getByRole('heading', { name: 'Visão geral', exact: true }).waitFor();
  assert.equal((await page.locator('.metric-value').allTextContents())[0], '1');
  await page.goto(`${baseUrl}/#governanca`);
  const downloaded = page.waitForEvent('download');
  await page.getByRole('link', { name: 'Exportar pacote de auditoria', exact: true }).click();
  const download = await downloaded;
  const exportPath = path.join(output, 'audit-package.json');
  await download.saveAs(exportPath);
  const packageData = JSON.parse(fs.readFileSync(exportPath, 'utf8'));
  assert.equal(packageData.format, 'elo-audit-v1');
  assert.equal(packageData.state.cases.length, 3);
  assert.equal(packageData.manifest.event_count, afterNoMatch.audit.length);
  const { spawnSync } = require('node:child_process');
  const verify = spawnSync('python3', ['backend/audit_export.py', exportPath], { encoding: 'utf8' });
  assert.equal(verify.status, 0, verify.stderr || verify.stdout);
  await page.close();

  const mobile = await browser.newPage({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
  mobile.on('pageerror', (error) => pageErrors.push(error.message));
  await mobile.goto(`${baseUrl}/#inteligencia`);
  await choose(mobile.locator('#selected-case'), 'ELO-2001 · Aguardando análise');
  await mobile.getByRole('button', { name: 'Abrir caso selecionado', exact: true }).tap();
  await mobile.getByRole('heading', { name: 'Possível conflito de interesses · ELO-2001', exact: true }).waitFor();
  await mobile.getByRole('heading', { name: 'Importar base sintética', exact: true }).tap();
  await input(mobile, '#import-dataset').waitFor({ state: 'visible' });
  await verifyDesignSystem(mobile, ['p-select', 'p-input-text', 'p-textarea', 'p-button', 'p-accordion']);
  await verifyTypography(mobile, '#import-actor', 'label');
  assert.ok(await mobile.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'Importação móvel não deve causar rolagem horizontal');
  await mobile.screenshot({ path: path.join(output, 'mobile-multiple-cases.png'), fullPage: true });
  await mobile.close();
}

async function main() {
  const response = await fetch(new URL('/api/state', baseUrl));
  assert.ok(response.ok, 'O servidor local do Elo precisa estar em execução.');
  const state = await response.json();
  assert.equal(state.case, null, 'Use um banco temporário vazio. O teste registra um caso completo.');

  const channel = process.env.PLAYWRIGHT_CHANNEL;
  const browser = await chromium.launch(channel ? { channel } : undefined);
  const pageErrors = [];
  try {
    await runDesktop(browser, pageErrors);
    await runMobile(browser, pageErrors);
    await runExpanded(browser, pageErrors);
    assert.deepEqual(pageErrors, []);
    console.log('Elo: jornada executável e navegação móvel verificadas com Playwright.');
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
