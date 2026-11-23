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

async function settleMotion(page) {
  await page.evaluate(async () => {
    await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
    await Promise.all(document.getAnimations().filter((animation) => Number.isFinite(animation.effect?.getTiming().iterations))
      .map((animation) => animation.finished.catch(() => {})));
  });
}

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
  )).filter((element) => !element.matches('p-tabs-bar > a, input[type=file][hidden][data-native-file-picker]')).map((element) => element.outerHTML));
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
  await settleMotion(page);
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
  const savedDossier = (await (await page.request.get(`${baseUrl}/api/state`)).json()).case.dossier;
  assert.ok(savedDossier.claims.length > 0);
  const renderedClaims = await page.getByTestId('dossier').locator('p-text-list-item').allTextContents();
  assert.equal(renderedClaims.length, savedDossier.claims.length);
  savedDossier.claims.forEach((claim, index) => {
    assert.ok(renderedClaims[index].includes(claim.text));
    claim.source_ids.forEach((id) => assert.ok(renderedClaims[index].includes(id), 'Cada afirmação deve exibir suas próprias fontes adjacentes'));
  });
  await page.getByText(aiMode === 'real' ? /^IA real · / : 'Síntese local baseada nas evidências').waitFor();
  await verifyDesignSystem(page, ['p-select', 'p-select-option', 'p-input-text', 'p-textarea', 'p-button', 'p-inline-notification']);
  await verifyTypography(page, '#decision-actor', 'label');
  await settleMotion(page);
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
  await settleMotion(page);
  await page.screenshot({ path: path.join(output, 'desktop-impactos.png'), fullPage: true });

  await page.getByRole('link', { name: 'Abrir plano e auditoria' }).click();
  await input(page, '#action-title').fill('Revisar a rotina de declaração');
  await input(page, '#action-owner').fill('Marco Demo');
  await input(page, '#action-due').fill('2027-01-15');
  await input(page, '#action-actor').fill('Lia Demo');
  await page.getByRole('button', { name: 'Criar plano de ação' }).click();
  const action = page.getByTestId('action-item');
  await action.getByText('Revisar a rotina de declaração', { exact: true }).waitFor();
  await action.getByRole('heading', { name: 'Anexar evidência de execução', exact: true }).click();
  let upload = action.locator('form[data-endpoint="evidence/upload"]');
  let chooserEvent = page.waitForEvent('filechooser');
  await upload.getByRole('button', { name: 'Selecionar arquivo de evidência', exact: true }).press('Enter');
  await (await chooserEvent).setFiles({ name: 'grande.txt', mimeType: 'text/plain', buffer: Buffer.alloc(1048577, 65) });
  await page.getByText('O arquivo excede o limite de 1 MiB.', { exact: true }).waitFor();
  const evidenceBytes = Buffer.from('Ata sintética DEMO-01. CTR-1042 e FOR-042: verificação esmeralda <b>literal</b>. Arquivo fictício para a jornada Elo.\n', 'utf8');
  chooserEvent = page.waitForEvent('filechooser');
  await upload.getByRole('button', { name: 'Selecionar arquivo de evidência', exact: true }).press('Enter');
  await (await chooserEvent).setFiles({ name: 'ata-sintetica.txt', mimeType: 'text/plain', buffer: evidenceBytes });
  await upload.getByText(`ata-sintetica.txt · ${evidenceBytes.length} bytes`, { exact: true }).waitFor();
  await upload.getByLabel('Descrição e relação com o caso').fill('Ata fictícia que documenta a execução da revisão.');
  await upload.getByLabel('Responsável pelo anexo').fill('Marco Demo');
  await upload.getByLabel('Confirmo que o arquivo contém somente dados fictícios').check();
  await upload.getByRole('button', { name: 'Anexar evidência', exact: true }).click();
  await action.getByRole('link', { name: 'Baixar ata-sintetica.txt', exact: true }).waitFor();
  const downloadEvent = page.waitForEvent('download');
  await action.getByRole('link', { name: 'Baixar ata-sintetica.txt', exact: true }).click();
  const evidenceDownload = await downloadEvent;
  const evidencePath = path.join(output, 'evidence-download.txt');
  await evidenceDownload.saveAs(evidencePath);
  assert.deepEqual(fs.readFileSync(evidencePath), evidenceBytes);
  const uploadedState = await (await page.request.get(`${baseUrl}/api/state`)).json();
  assert.equal(uploadedState.attachments[0].sha256, require('node:crypto').createHash('sha256').update(evidenceBytes).digest('hex'));
  await verifyDesignSystem(page, ['p-input-date', 'p-accordion', 'p-text-list', 'p-tag', 'p-button']);
  await action.getByText('Atualizar andamento', { exact: true }).click();
  await choose(action.locator('p-select[name=status]'), 'Em andamento');
  await action.getByLabel('Quem está registrando').fill('Marco Demo');
  await action.getByRole('button', { name: 'Salvar andamento' }).click();
  await action.locator('.badge').getByText('Em andamento', { exact: true }).waitFor();
  await action.getByText('Atualizar andamento', { exact: true }).click();
  await choose(action.locator('p-select[name=status]'), 'Aguardando aprovação de encerramento');
  await action.getByLabel('Quem está registrando').fill('Marco Demo');
  await action.getByLabel('Evidência de execução').fill('Ata sintética DEMO-01.');
  await action.getByRole('button', { name: 'Salvar andamento' }).click();
  await action.locator('.badge').getByText('Aguardando aprovação de encerramento', { exact: true }).waitFor();
  await choose(action.locator('p-select[name=outcome]'), 'Aprovar encerramento');
  await action.getByLabel('Revisor do encerramento').fill('Marco Demo');
  await action.getByLabel('Justificativa da revisão').fill('Evidência de execução conferida.');
  await action.getByRole('button', { name: 'Registrar revisão de encerramento' }).click();
  await page.getByText('A revisão exige uma pessoa diferente de quem solicitou o encerramento.', { exact: true }).waitFor();
  await action.getByLabel('Revisor do encerramento').fill('Rita Demo');
  await action.getByRole('button', { name: 'Registrar revisão de encerramento' }).click();
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
  await settleMotion(page);
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
    await settleMotion(page);
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
  await page.getByText('3 indício(s) registrado(s). Cada regra requer análise e revisão humana independentes.', { exact: true }).waitFor();
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
  await settleMotion(page);
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
  assert.ok(['elo-audit-v1', 'elo-audit-v2'].includes(packageData.format));
  assert.equal(packageData.state.cases.length, 3);
  assert.equal(packageData.files.length, 1);
  assert.equal(packageData.state.attachments.length, 1);
  assert.deepEqual(Buffer.from(packageData.files[0].content_base64, 'base64'), fs.readFileSync(path.join(output, 'evidence-download.txt')));
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
  await settleMotion(mobile);
  await mobile.screenshot({ path: path.join(output, 'mobile-multiple-cases.png'), fullPage: true });
  await mobile.close();
}

async function runGovernance(browser, pageErrors) {
  const page = await browser.newPage({ viewport: { width: 1440, height: 950 }, locale: 'pt-BR' });
  page.on('pageerror', (error) => pageErrors.push(error.message));
  const snapshot = async () => (await page.request.get(`${baseUrl}/api/state`)).json();
  const fillAudit = async (form, reason) => {
    await form.getByLabel('Responsável pelo registro').fill('Gestora Demo');
    await form.getByLabel('Justificativa do registro').fill(reason);
  };
  const save = async (form, label) => {
    const response = page.waitForResponse((response) => response.request().method() === 'POST' && response.url().includes('/api/'));
    await form.getByRole('button', { name: label, exact: true }).click();
    const result = await response;
    assert.ok(result.ok(), await result.text());
    await page.getByText('Registro atualizado.', { exact: true }).waitFor();
  };
  await page.goto(`${baseUrl}/?case_id=ELO-2001#impactos`);
  await page.getByRole('heading', { name: 'Novo controle', exact: true }).click();
  let form = page.getByTestId('control-new');
  await form.getByLabel('Nome do controle').fill('Conferência sintética de vínculos');
  await form.getByLabel('Descrição do controle').fill('Conferência por duas pessoas antes da aprovação.');
  await fillAudit(form, 'Ampliar a cobertura do catálogo sintético.');
  await save(form, 'Criar controle');
  const control = (await snapshot()).controls.find((item) => item.name === 'Conferência sintética de vínculos');
  assert.ok(control);
  await page.getByTestId(`catalog-${control.id}`).getByRole('heading', { name: 'Editar controle', exact: true }).click();
  form = page.getByTestId(`control-${control.id}`);
  await form.getByLabel('Descrição do controle').fill('Conferência e registro de evidência por duas pessoas.');
  await fillAudit(form, 'Detalhar a evidência esperada.');
  await save(form, 'Salvar controle');
  assert.match((await snapshot()).controls.find((item) => item.id === control.id).description, /registro de evidência/);

  await page.getByRole('heading', { name: 'Novo risco', exact: true }).click();
  form = page.getByTestId('risk-new');
  await form.getByLabel('Nome do risco').fill('Risco sintético de contratação');
  await form.getByLabel('Conferência sintética de vínculos').check();
  await fillAudit(form, 'Relacionar controle ao risco específico do lote.');
  await save(form, 'Criar risco');
  const risk = (await snapshot()).risks.find((item) => item.name === 'Risco sintético de contratação');
  assert.deepEqual(risk.control_ids, [control.id]);

  await page.getByRole('heading', { name: 'Nova dimensão', exact: true }).click();
  form = page.getByTestId('dimension-new');
  await form.getByLabel('Nome da dimensão').fill('Verificação sintética de terceiros');
  await form.locator('p-input-text[name=question_text_0]').getByRole('textbox').fill('As verificações possuem evidências?');
  await fillAudit(form, 'Criar metodologia ilustrativa com uma pergunta.');
  await save(form, 'Criar dimensão');
  const dimension = (await snapshot()).dimensions.find((item) => item.name === 'Verificação sintética de terceiros');
  assert.equal(dimension.questions.length, 1);
  let dimensionPanel = page.getByTestId(`catalog-${dimension.id}`);
  await dimensionPanel.getByRole('heading', { name: 'Responder questionário', exact: true }).click();
  form = page.getByTestId(`assessment-${dimension.id}`);
  await form.getByRole('spinbutton', { name: /Pontuação/ }).fill('2');
  await form.getByLabel('Evidência que sustenta a pontuação').fill('Amostra sintética: duas evidências disponíveis de cinco previstas.');
  await fillAudit(form, 'Avaliação humana da lacuna na amostra.');
  await form.getByLabel('Revisei as evidências e confirmo esta avaliação humana').check();
  await save(form, 'Registrar avaliação de maturidade');
  const assessment = (await snapshot()).assessments.at(-1);
  assert.equal(assessment.score, 40);
  assert.equal(assessment.level, 'Intermediária');
  assert.equal(assessment.answers[0].gap, 3);
  await page.getByTestId('assessments').getByText(/Lacuna 3/).waitFor();
  await verifyDesignSystem(page, ['p-checkbox', 'p-input-number', 'p-accordion', 'p-select']);
  await settleMotion(page);
  await page.screenshot({ path: path.join(output, 'desktop-governance-catalogs.png'), fullPage: true });

  await page.goto(`${baseUrl}/?case_id=ELO-2001#inteligencia`);
  form = page.getByTestId('case-links');
  await choose(form.locator('#case-risk'), risk.name);
  await choose(form.locator('#case-dimension'), dimension.name);
  await fillAudit(form, 'Direcionar a análise aos registros específicos.');
  await save(form, 'Salvar vínculos do caso');
  assert.equal((await snapshot()).cases.find((item) => item.id === 'ELO-2001').risk_id, risk.id);
  await choose(page.locator('#dossier-mode'), 'Síntese local');
  await page.getByTestId('generate-dossier').click();
  await page.getByTestId('dossier').waitFor();
  await choose(page.locator('#decision-review'), 'Aceitar');
  await choose(page.locator('#decision-outcome'), 'Registrar fragilidade');
  await input(page, '#decision-actor').fill('Analista Demo 3');
  await input(page, '#decision-reason').fill('A fragilidade demanda avaliação dos controles deste risco.');
  await page.getByRole('button', { name: 'Registrar decisão', exact: true }).click();
  await page.getByTestId('case-decision').getByText('Aceitou a sugestão', { exact: true }).waitFor();
  await page.getByRole('link', { name: 'Avaliar impacto em risco e maturidade' }).click();
  await page.getByText(risk.name, { exact: true }).first().waitFor();
  await decideImpact(page, 'risk', 'approved', 'Exposição ampliada após análise humana do vínculo.');
  await decideImpact(page, 'maturity', 'rejected', 'Preservar avaliação baseada no questionário; ampliar amostra antes de alterar.');
  const afterImpacts = await snapshot();
  assert.equal(afterImpacts.risks.find((item) => item.id === risk.id).level, 'Alta');
  assert.equal(afterImpacts.dimensions.find((item) => item.id === dimension.id).level, 'Intermediária');

  await page.goto(`${baseUrl}/?case_id=ELO-2001#governanca`);
  await input(page, '#action-title').fill('Revisar evidências do segundo caso');
  await input(page, '#action-owner').fill('Executora Demo');
  await input(page, '#action-due').fill('2027-02-20');
  await input(page, '#action-actor').fill('Gestora Demo');
  await page.getByRole('button', { name: 'Criar plano de ação' }).click();
  const action = page.getByTestId('action-item').filter({ hasText: 'Revisar evidências do segundo caso' });
  await action.getByRole('heading', { name: 'Editar responsável e prazo', exact: true }).click();
  form = action.locator('form[data-endpoint="action/edit"]');
  await form.getByLabel('Pessoa responsável').fill('Nova Executora Demo');
  await form.getByLabel('Prazo').fill('2027-03-01');
  await fillAudit(form, 'Redistribuição da execução com prazo revisado.');
  await save(form, 'Salvar responsável e prazo');
  await action.getByText(/Nova Executora Demo · Prazo 2027-03-01/).waitFor();

  await page.getByRole('heading', { name: 'Novo relatório gerencial', exact: true }).click();
  form = page.getByTestId('report-create');
  await form.getByLabel('Título do relatório').fill('Relatório sintético com concordância e rejeição');
  await form.getByLabel('ELO-1042 · Fragilidade registrada').check();
  await form.getByLabel('ELO-2002 · Descartado').check();
  await form.getByLabel('Responsável pela compilação').fill('Relatora Demo');
  await save(form, 'Criar rascunho de relatório');
  let report = (await snapshot()).reports[0];
  assert.equal(report.cases[1].claim_status, 'excluded_by_human_rejection');
  assert.deepEqual(report.cases[1].claims, []);
  const reportCard = page.getByTestId(`report-${report.id}`);
  const reportClaims = await reportCard.getByTestId('report-claims').locator('p-text-list-item').allTextContents();
  report.cases[0].claims.forEach((claim, index) => {
    assert.ok(reportClaims[index].includes(claim.text));
    claim.source_ids.forEach((id) => assert.ok(reportClaims[index].includes(id)));
  });
  await reportCard.getByRole('heading', { name: 'Fontes preservadas · ELO-1042', exact: true }).click();
  await reportCard.getByText(/"id": "CTR-1042"/).waitFor();
  const reviewReport = reportCard.locator('form[data-endpoint="report/review"]');
  await choose(reviewReport.locator('p-select[name=outcome]'), 'Aprovar relatório');
  await reviewReport.getByLabel('Revisor do relatório').fill('Revisora de Relatório Demo');
  await reviewReport.getByLabel('Justificativa da revisão do relatório').fill('Afirmações, decisões humanas, fontes e limitações conferidas.');
  await save(reviewReport, 'Registrar revisão do relatório');
  assert.equal((await snapshot()).reports[0].status, 'approved');
  await page.getByTestId('report-RPT-001').getByRole('heading', { name: 'Relatório sintético com concordância e rejeição · RPT-001', exact: true }).scrollIntoViewIfNeeded();
  await settleMotion(page);
  await page.screenshot({ path: path.join(output, 'desktop-report.png') });
  await page.getByRole('button', { name: 'Atualizar indicadores de supervisão', exact: true }).click();
  await page.getByTestId('supervision-summary').getByText('Síntese local', { exact: true }).waitFor();
  await page.getByTestId('supervision-summary').getByText(/Código sintético compartilhado por coincidência/).waitFor();
  await page.goto(`${baseUrl}/?case_id=ELO-2001#inteligencia`);
  const beforeLab = await snapshot();
  await page.getByRole('button', { name: 'Executar laboratório sintético', exact: true }).click();
  await page.getByTestId('laboratory-result').getByText(/Precisão:/).waitFor();
  assert.deepEqual(await snapshot(), beforeLab, 'Laboratório não pode alterar o estado operacional');
  await settleMotion(page);
  await page.screenshot({ path: path.join(output, 'desktop-laboratory.png'), fullPage: true });
  await page.close();

  const mobile = await browser.newPage({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
  mobile.on('pageerror', (error) => pageErrors.push(error.message));
  await mobile.goto(`${baseUrl}/#impactos`);
  dimensionPanel = mobile.getByTestId(`catalog-${dimension.id}`);
  await dimensionPanel.getByRole('heading', { name: 'Responder questionário', exact: true }).tap();
  await mobile.getByTestId(`assessment-${dimension.id}`).getByRole('spinbutton').waitFor({ state: 'visible' });
  await verifyDesignSystem(mobile, ['p-checkbox', 'p-input-number', 'p-textarea', 'p-input-text', 'p-button']);
  await verifyTypography(mobile, `#assessment-${dimension.id}-actor`, 'label');
  assert.ok(await mobile.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'Questionário móvel não deve causar rolagem horizontal');
  await settleMotion(mobile);
  await mobile.screenshot({ path: path.join(output, 'mobile-maturity-questionnaire.png'), fullPage: true });
  const mobileAssessment = mobile.getByTestId(`assessment-${dimension.id}`);
  await mobileAssessment.getByRole('spinbutton').scrollIntoViewIfNeeded();
  await settleMotion(mobile);
  await mobile.screenshot({ path: path.join(output, 'mobile-maturity-question.png') });
  await mobileAssessment.getByLabel('Justificativa do registro').fill('Conferência visual e avaliação humana em dispositivo móvel.');
  await settleMotion(mobile);
  await mobile.screenshot({ path: path.join(output, 'mobile-maturity-confirmation.png') });
  const submitAssessment = mobileAssessment.getByRole('button', { name: 'Registrar avaliação de maturidade', exact: true });
  await mobileAssessment.getByRole('spinbutton').fill('3');
  await mobileAssessment.getByLabel('Evidência que sustenta a pontuação').fill('Amostra sintética revisada em dispositivo móvel.');
  await mobileAssessment.getByLabel('Responsável pelo registro').fill('Revisora Mobile Demo');
  await mobileAssessment.getByLabel('Revisei as evidências e confirmo esta avaliação humana').check();
  await submitAssessment.scrollIntoViewIfNeeded();
  await settleMotion(mobile);
  const submitLayout = await submitAssessment.evaluate((button) => {
    const style = getComputedStyle(button), rect = button.getBoundingClientRect();
    return { visibility: style.visibility, opacity: style.opacity, top: rect.y, bottom: rect.bottom, height: rect.height, viewport: innerHeight };
  });
  assert.equal(submitLayout.visibility, 'visible');
  assert.equal(submitLayout.opacity, '1');
  assert.ok(submitLayout.top >= 0 && submitLayout.bottom <= submitLayout.viewport && submitLayout.height > 0);
  await submitAssessment.screenshot({ path: path.join(output, 'mobile-maturity-submit.png') });
  await mobile.screenshot({ path: path.join(output, 'mobile-maturity-confirmation.png') });
  await submitAssessment.click();
  await mobile.getByTestId('assessments').getByText(/AVA-002/).waitFor();
  assert.equal((await (await mobile.request.get(`${baseUrl}/api/state`)).json()).assessments.at(-1).actor, 'Revisora Mobile Demo');
  assert.equal((await (await mobile.request.get(`${baseUrl}/api/state`)).json()).assessments.at(-1).score, 60);
  await mobile.goto(`${baseUrl}/#governanca`);
  await mobile.getByRole('heading', { name: 'Anexar arquivo ao caso', exact: true }).tap();
  const mobileUpload = mobile.getByTestId('upload-ELO-1042-case');
  const mobileFileChooser = mobile.waitForEvent('filechooser');
  await mobileUpload.getByRole('button', { name: 'Selecionar arquivo de evidência', exact: true }).tap();
  await (await mobileFileChooser).setFiles({ name: 'nota-mobile.txt', mimeType: 'text/plain', buffer: Buffer.from('Nota sintética FOR-9999 <script>window.unsafeDocument=true</script> anexada no celular.') });
  await mobileUpload.getByLabel('Descrição e relação com o caso').fill('Nota fictícia do caso registrada em dispositivo móvel.');
  await mobileUpload.getByLabel('Responsável pelo anexo').fill('Analista Mobile Demo');
  await mobileUpload.getByLabel('Confirmo que o arquivo contém somente dados fictícios').check();
  await mobileUpload.getByRole('button', { name: 'Anexar evidência', exact: true }).scrollIntoViewIfNeeded();
  await settleMotion(mobile);
  await mobile.screenshot({ path: path.join(output, 'mobile-evidence-upload.png') });
  await mobileUpload.getByRole('button', { name: 'Anexar evidência', exact: true }).tap();
  await mobile.getByRole('link', { name: 'Baixar nota-mobile.txt', exact: true }).waitFor();
  await mobile.getByTestId('report-RPT-001').getByRole('heading', { name: 'Relatório sintético com concordância e rejeição · RPT-001', exact: true }).scrollIntoViewIfNeeded();
  await settleMotion(mobile);
  assert.ok(await mobile.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'Relatório móvel não deve causar rolagem horizontal');
  await mobile.screenshot({ path: path.join(output, 'mobile-report.png') });

  await mobile.close();
}

async function runInsights(browser, pageErrors) {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  page.on('pageerror', (error) => pageErrors.push(error.message));
  const snapshot = async () => (await page.request.get(`${baseUrl}/api/state?case_id=ELO-2001`)).json();
  await page.goto(`${baseUrl}/?case_id=ELO-2001#inteligencia`);
  await page.getByTestId('similar-cases').getByRole('link', { name: 'Abrir ELO-2002', exact: true }).click();
  await page.getByTestId('case-decision').getByText(/Descartado/).waitFor();
  assert.equal(new URL(page.url()).searchParams.get('case_id'), 'ELO-2002');
  await page.goto(`${baseUrl}/?case_id=ELO-2001#impactos`);
  await page.getByTestId('case-connections').getByText(/proposta de impacto/).first().waitFor();
  const before = await snapshot();
  const form = page.getByTestId('scenario-form');
  await form.getByLabel('Probabilidade').fill('5');
  await form.getByLabel('Impacto', { exact: false }).fill('5');
  await form.getByLabel('Responsável pelo registro').fill('Simuladora Demo');
  await form.getByLabel('Justificativa do registro').fill('Hipótese sintética extrema para avaliar o tratamento.');
  await form.getByRole('button', { name: 'Registrar cenário hipotético', exact: true }).click();
  await page.getByTestId('scenario-SIM-001').getByText(/Hipótese Crítica/).waitFor();
  const after = await snapshot();
  assert.deepEqual(after.risks, before.risks, 'Simulação não pode alterar avaliação ou revisão dos riscos');
  assert.equal(after.scenarios[0].score, 25);
  await page.getByTestId('scenario-SIM-001').scrollIntoViewIfNeeded();
  await settleMotion(page);
  await page.screenshot({ path: path.join(output, 'desktop-scenario.png') });
  await page.goto(`${baseUrl}/#visao`);
  await page.getByTestId('event-trends').waitFor();
  await verifyDesignSystem(page, ['p-table', 'p-table-head-cell', 'p-table-cell']);
  const context = await (await page.request.get(`${baseUrl}/api/insights?case_id=ELO-2001`)).json();
  const sum = (key) => context.trends.periods.reduce((total, row) => total + row[key], 0);
  assert.equal(sum('detected'), 3);
  assert.equal(sum('qualified'), 2);
  assert.equal(sum('discarded'), 1);
  assert.equal(sum('completed'), 1);
  await page.goto(`${baseUrl}/?case_id=ELO-2001#inteligencia`);
  await page.getByRole('heading', { name: 'Importar base sintética', exact: true }).click();
  await input(page, '#import-dataset').fill(JSON.stringify({ employees: [], contracts: [], suppliers: [{ id: 'FOR-201', name: 'Fornecedor sintético relacionado', contact_code: 'FICT-200' }] }));
  await input(page, '#import-actor').fill('Importador de cenário');
  await choose(page.locator('#import-synthetic'), 'Confirmo que todos os dados são fictícios');
  await page.getByRole('button', { name: 'Importar base', exact: true }).click();
  await page.getByText('Registro atualizado.', { exact: true }).waitFor();
  await page.getByTestId('detect-suppliers').click();
  await page.waitForFunction(() => document.querySelector('#view')?.getAttribute('aria-busy') === 'false' && document.querySelector('[data-testid="detect-suppliers"]')?.disabled);
  const secondary = await snapshot();
  const related = secondary.cases.find((item) => item.rule.id === 'supplier-shared-contact');
  assert.ok(related);
  assert.deepEqual(secondary.cases.filter((item) => item.rule.id === 'contact-code-match'), after.cases);
  await page.goto(`${baseUrl}/?case_id=${related.id}#inteligencia`);
  await page.getByRole('heading', { name: `Cadastro compartilhado entre fornecedores · ${related.id}`, exact: true }).waitFor();
  assert.equal(await page.getByTestId('evidence-list').getByRole('heading', { name: 'Abrir registro FOR-201', exact: true }).count(), 1);
  await choose(page.locator('#dossier-mode'), aiMode === 'real' ? 'IA real (requer configuração)' : 'Síntese local');
  await page.getByTestId('generate-dossier').click();
  await page.getByTestId('dossier').waitFor({ timeout: 120000 });
  const secondaryDossier = (await (await page.request.get(`${baseUrl}/api/state?case_id=${related.id}`)).json()).case.dossier;
  assert.ok(secondaryDossier.claims.length);
  assert.ok(secondaryDossier.claims.every((claim) => claim.source_ids.every((id) => related.evidence.some((source) => source.id === id))));
  assert.ok(secondaryDossier.source_ids.includes('FOR-201'));
  assert.ok(!secondaryDossier.source_ids.some((id) => id.startsWith('EMP-')));

  await page.close();

  const mobile = await browser.newPage({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
  mobile.on('pageerror', (error) => pageErrors.push(error.message));
  await mobile.goto(`${baseUrl}/#visao`);
  await mobile.getByTestId('event-trends').scrollIntoViewIfNeeded();
  await settleMotion(mobile);
  assert.ok(await mobile.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'Tabela móvel deve rolar internamente');
  await mobile.screenshot({ path: path.join(output, 'mobile-trends.png') });
  await mobile.goto(`${baseUrl}/?case_id=ELO-2001#impactos`);
  const mobileForm = mobile.getByTestId('scenario-form');
  await mobileForm.getByLabel('Probabilidade').fill('1');
  await mobileForm.getByLabel('Impacto').fill('1');
  await mobileForm.getByLabel('Responsável pelo registro').fill('Simuladora Mobile');
  await mobileForm.getByLabel('Justificativa do registro').fill('Hipótese mínima registrada no celular.');
  await mobileForm.getByRole('button', { name: 'Registrar cenário hipotético', exact: true }).tap();
  await mobile.getByTestId('scenario-SIM-002').getByText(/Hipótese Baixa/).waitFor();
  assert.deepEqual((await (await mobile.request.get(`${baseUrl}/api/state`)).json()).risks, before.risks);
  await mobile.getByTestId('scenario-SIM-002').scrollIntoViewIfNeeded();
  await settleMotion(mobile);
  assert.ok(await mobile.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
  await mobile.screenshot({ path: path.join(output, 'mobile-scenario.png') });
  await mobile.close();
}

async function runAssistant(browser, pageErrors) {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  page.on('pageerror', (error) => pageErrors.push(error.message));
  await page.goto(`${baseUrl}/?case_id=ELO-1042#inteligencia`);
  const snapshot = async () => (await page.request.get(`${baseUrl}/api/state?case_id=ELO-1042`)).json();
  const before = await snapshot();
  let form = page.getByTestId('assistant-form');
  await form.getByLabel('Pergunta sobre este caso').fill('Qual é o risco vigente deste caso?');
  await form.getByLabel('Responsável pela consulta').fill('Consultora Demo');
  await page.route('**/api/assistant/query', async (route) => {
    await route.fulfill({ status: 409, contentType: 'application/json', body: JSON.stringify({ error: 'As fontes mudaram durante a consulta. Revise o caso e faça uma nova pergunta.' }) });
  }, { times: 1 });
  await form.getByRole('button', { name: 'Consultar fontes do caso', exact: true }).click();
  await page.getByText('As fontes mudaram durante a consulta. Revise o caso e faça uma nova pergunta.', { exact: true }).waitFor();
  assert.equal(await form.getByLabel('Pergunta sobre este caso').inputValue(), 'Qual é o risco vigente deste caso?');
  assert.equal((await snapshot()).assistant_queries.length, 0);
  await form.getByRole('button', { name: 'Consultar fontes do caso', exact: true }).click();
  await page.getByTestId('assistant-ASK-001').getByTestId('assistant-claims').getByText('Fontes: RSK-001', { exact: true }).waitFor();
  await page.getByRole('heading', { name: 'Consultar fontes preservadas · ASK-001', exact: true }).click();
  await page.getByTestId('assistant-ASK-001').getByText('RSK-001 · Risco vigente', { exact: true }).waitFor();
  form = page.getByTestId('assistant-form');
  await form.getByLabel('Pergunta sobre este caso').fill('Astronomia galáxias desconhecidas?');
  await form.getByLabel('Responsável pela consulta').fill('Consultora Demo');
  await form.getByRole('button', { name: 'Consultar fontes do caso', exact: true }).click();
  await page.getByTestId('assistant-ASK-002').getByText('Sem resposta sustentada pelas fontes', { exact: true }).waitFor();
  if (aiMode === 'real') {
    form = page.getByTestId('assistant-form');
    await form.getByLabel('Pergunta sobre este caso').fill('Qual é a exposição vigente do risco deste caso?');
    await form.getByLabel('Responsável pela consulta').fill('Consultora IA Demo');
    await choose(page.locator('#assistant-mode'), 'IA real (requer configuração)');
    await form.getByRole('button', { name: 'Consultar fontes do caso', exact: true }).click();
    await page.getByTestId('assistant-ASK-003').waitFor({ timeout: 120000 });
    const response = (await snapshot()).assistant_queries.at(-1);
    assert.equal(response.mode, 'real');
    assert.equal(response.abstained, false);
    assert.ok(response.claims.some((claim) => claim.source_ids.includes('RSK-001')));
    const rendered = await page.getByTestId('assistant-ASK-003').getByTestId('assistant-claims').locator('p-text-list-item').allTextContents();
    response.claims.forEach((claim, index) => claim.source_ids.forEach((id) => assert.ok(rendered[index].includes(id))));
  }
  const after = await snapshot();
  for (const key of ['cases', 'risks', 'dimensions', 'actions', 'attachments', 'reports', 'assessments', 'scenarios', 'dataset', 'work_items', 'document_analyses']) assert.deepEqual(after[key], before[key], `Consulta não altera ${key}`);
  assert.equal(after.assistant_queries[1].abstained, true);
  await page.getByTestId('assistant-ASK-002').scrollIntoViewIfNeeded();
  await settleMotion(page);
  await page.screenshot({ path: path.join(output, 'desktop-assistant.png') });
  await page.goto(`${baseUrl}/?case_id=ELO-2001#inteligencia`);
  assert.equal(await page.getByTestId('assistant-ASK-001').count(), 0, 'Histórico restrito ao caso selecionado');
  await page.close();
  const mobile = await browser.newPage({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
  mobile.on('pageerror', (error) => pageErrors.push(error.message));
  await mobile.goto(`${baseUrl}/?case_id=ELO-1042#inteligencia`);
  await mobile.getByTestId('assistant-ASK-001').scrollIntoViewIfNeeded();
  await settleMotion(mobile);
  assert.ok(await mobile.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
  await mobile.screenshot({ path: path.join(output, 'mobile-assistant.png') });
  await mobile.close();
}

async function createWork(page, title, priority = 'Alta') {
  await page.getByRole('heading', { name: 'Planejar novo trabalho', exact: true }).click();
  const form = page.getByTestId('work-new');
  await form.getByLabel('Título do trabalho').fill(title);
  await form.getByLabel('Objetivo e escopo do trabalho').fill('Verificar a documentação sintética dos controles da segunda linha.');
  await form.getByLabel('Responsável pela execução').fill('Executora Demo');
  await form.getByLabel('Prazo do trabalho').fill('2020-01-01');
  await choose(form.locator('p-select[name=priority]'), priority);
  await form.getByLabel('Justificativa da prioridade').fill('Amostra sintética priorizada por exposição e necessidade de revisão.');
  await form.getByLabel('Responsável pelo registro').fill('Planejadora Demo');
  await form.getByLabel('Justificativa do registro').fill('Planejamento independente de trabalho da segunda linha.');
  await form.getByRole('button', { name: 'Planejar trabalho', exact: true }).click();
  await page.getByText('Registro atualizado.', { exact: true }).waitFor();
}

async function runIndependentWorks(browser, pageErrors) {
  const page = await browser.newPage({ viewport: { width: 1440, height: 950 } });
  page.on('pageerror', (error) => pageErrors.push(error.message));
  await page.goto(`${baseUrl}/#governanca`);
  await page.getByTestId('work-summary').getByText(/0 trabalho\(s\)/).waitFor();
  await createWork(page, 'Revisão independente sem indício');
  await page.getByTestId('work-item-WRK-001').locator('.work-status').getByText('Planejado', { exact: true }).waitFor();
  let saved = await (await page.request.get(`${baseUrl}/api/state`)).json();
  assert.equal(saved.case, null);
  assert.deepEqual(saved.work_items[0].case_ids, []);
  await page.getByRole('heading', { name: 'Iniciar execução · WRK-001', exact: true }).click();
  let form = page.getByTestId('work-WRK-001-in_progress');
  await form.getByLabel('Responsável pelo registro').fill('Executora Demo');
  await form.getByLabel('Justificativa do registro').fill('Início da revisão documental sintética.');
  await form.getByRole('button', { name: 'Iniciar trabalho', exact: true }).click();
  await page.getByTestId('work-item-WRK-001').locator('.work-status').getByText('Em execução', { exact: true }).waitFor();
  await page.getByRole('heading', { name: 'Concluir trabalho · WRK-001', exact: true }).click();
  form = page.getByTestId('work-WRK-001-completed');
  await form.getByLabel('Responsável pelo registro').fill('Executora Demo');
  await form.getByLabel('Justificativa do registro').fill('Revisão encerrada com resultado documentado.');
  const activeWork = (await (await page.request.get(`${baseUrl}/api/state`)).json()).work_items[0];
  const emptyCompletion = await page.request.post(`${baseUrl}/api/work/status`, { data: { id: activeWork.id, revision: activeWork.revision, status: 'completed', actor: 'Executora Demo', reason: 'Conclusão sem resultado deve ser recusada.', result: '' } });
  assert.equal(emptyCompletion.status(), 422);
  assert.equal((await (await page.request.get(`${baseUrl}/api/state`)).json()).work_items[0].status, 'in_progress', 'Resultado obrigatório impede conclusão vazia');
  await form.getByLabel('Resultado e entregas do trabalho').fill('Amostra sintética revisada; documentação de controle conferida.');
  await form.getByRole('button', { name: 'Concluir trabalho', exact: true }).click();
  await page.getByTestId('work-item-WRK-001').locator('.work-status').getByText('Concluído', { exact: true }).waitFor();
  assert.equal(await page.getByTestId('work-item-WRK-001').locator('form').count(), 0);
  await createWork(page, 'Trabalho sintético para replanejar', 'Urgente');
  await page.getByTestId('work-item-WRK-002').waitFor();
  const summary = await (await page.request.get(`${baseUrl}/api/work/summary`)).json();
  assert.equal(summary.pending, 1);
  assert.equal(summary.overdue, 1);
  assert.equal(summary.completion_rate.numerator, 1);
  assert.equal(summary.completion_rate.denominator, 2);
  assert.equal(summary.treatment_time.completed_with_timing, 1);
  await verifyDesignSystem(page, ['p-input-date', 'p-select', 'p-textarea', 'p-table']);
  await page.getByRole('heading', { name: 'Planejar novo trabalho', exact: true }).click();
  await verifyTypography(page, '#work-new-owner', 'label');
  await page.getByTestId('work-summary').scrollIntoViewIfNeeded();
  await settleMotion(page);
  await page.screenshot({ path: path.join(output, 'desktop-work-summary.png') });
  await page.close();
}

async function runWorkUpdates(browser, pageErrors) {
  const page = await browser.newPage({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
  page.on('pageerror', (error) => pageErrors.push(error.message));
  await page.goto(`${baseUrl}/#governanca`);
  await page.getByRole('heading', { name: 'Editar planejamento · WRK-002', exact: true }).tap();
  const form = page.getByTestId('work-WRK-002');
  await form.getByLabel('ELO-1042 · Possível conflito de interesses', { exact: true }).check();
  await choose(form.locator('p-select[name=priority]'), 'Normal');
  await form.getByLabel('Justificativa da prioridade').fill('Replanejamento após revisão da amostra sintética.');
  await form.getByLabel('Responsável pelo registro').fill('Planejadora Mobile');
  await form.getByLabel('Justificativa do registro').fill('Vincular indício e atualizar prioridade do trabalho.');
  await form.getByRole('button', { name: 'Salvar trabalho', exact: true }).tap();
  await page.getByTestId('work-item-WRK-002').getByRole('link', { name: 'Consultar ELO-1042', exact: true }).waitFor();
  const state = await (await page.request.get(`${baseUrl}/api/state`)).json();
  const item = state.work_items.find((work) => work.id === 'WRK-002');
  assert.equal(item.priority, 'normal');
  assert.deepEqual(item.case_ids, ['ELO-1042']);
  await page.getByRole('heading', { name: 'Cancelar trabalho · WRK-002', exact: true }).tap();
  const cancel = page.getByTestId('work-WRK-002-cancelled');
  await cancel.getByLabel('Responsável pelo registro').fill('Planejadora Mobile');
  await cancel.getByLabel('Justificativa do registro').fill('Escopo sintético absorvido pela revisão concluída.');
  await cancel.getByRole('button', { name: 'Cancelar trabalho', exact: true }).scrollIntoViewIfNeeded();
  await settleMotion(page);
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
  await page.screenshot({ path: path.join(output, 'mobile-work-cancel.png') });
  await cancel.getByRole('button', { name: 'Cancelar trabalho', exact: true }).tap();
  await page.getByTestId('work-item-WRK-002').locator('.work-status').getByText('Cancelado', { exact: true }).waitFor();
  const summary = await (await page.request.get(`${baseUrl}/api/work/summary`)).json();
  assert.equal(summary.pending, 0);
  assert.equal(summary.overdue, 0);
  assert.equal(summary.completion_rate.denominator, 1, 'Cancelamento sai do denominador de conclusão');
  assert.equal(summary.treatment_time.completed_total, 1);
  assert.deepEqual((await (await page.request.get(`${baseUrl}/api/state`)).json()).cases, state.cases, 'Trabalho não altera os casos vinculados');
  await page.getByTestId('work-priorities').scrollIntoViewIfNeeded();
  await settleMotion(page);
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
  await page.screenshot({ path: path.join(output, 'mobile-work-summary.png') });
  await page.close();
}

async function runRuleConfiguration(browser, pageErrors) {
  const page = await browser.newPage({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
  page.on('pageerror', (error) => pageErrors.push(error.message));
  await page.goto(`${baseUrl}/?case_id=ELO-1042#inteligencia`);
  const before = await (await page.request.get(`${baseUrl}/api/state`)).json();
  const rule = before.rules.find((entry) => entry.id === 'contact-code-match');
  await page.getByRole('heading', { name: `Configurar regra · ${rule.name}`, exact: true }).tap();
  const form = page.getByTestId('rule-config-contact-code-match');
  await form.getByLabel('Regra habilitada').uncheck();
  await form.getByLabel('Comprimento mínimo do código').fill('2');
  await form.getByLabel('Responsável pelo registro').fill('Revisora Regras Mobile');
  await form.getByLabel('Justificativa do registro').fill('Desativação sintética para aferir falsos negativos no gabarito.');
  await form.getByRole('button', { name: 'Salvar parâmetros da regra', exact: true }).scrollIntoViewIfNeeded();
  await settleMotion(page);
  await page.screenshot({ path: path.join(output, 'mobile-rule-configuration.png') });
  await form.getByRole('button', { name: 'Salvar parâmetros da regra', exact: true }).tap();
  await page.getByText('Configuração v2 · Desativada · Comprimento mínimo: 2', { exact: true }).waitFor();
  assert.equal(await page.getByTestId('detect').getByRole('button').isDisabled(), true);
  const after = await (await page.request.get(`${baseUrl}/api/state`)).json();
  assert.deepEqual(after.cases, before.cases, 'Reconfiguração preserva casos e parâmetros da detecção original');
  assert.equal(after.rules.find((entry) => entry.id === rule.id).configuration.version, 2);
  const stale = await page.request.post(`${baseUrl}/api/rule/config`, { data: { ...rule.configuration, actor: 'Revisora Demo', reason: 'Versão antiga recusada.' } });
  assert.equal(stale.status(), 409);
  await page.getByRole('button', { name: 'Executar laboratório sintético', exact: true }).tap();
  await page.getByTestId('laboratory-result').getByText('Sinais não encontrados: 2', { exact: true }).waitFor();
  await choose(page.locator('#laboratory-rule'), 'Cadastro compartilhado entre fornecedores');
  await page.getByRole('button', { name: 'Executar laboratório sintético', exact: true }).tap();
  await page.getByTestId('laboratory-result').getByText(/Regra: Cadastro compartilhado entre fornecedores/).waitFor();
  assert.deepEqual((await (await page.request.get(`${baseUrl}/api/state`)).json()).cases, before.cases);
  await page.getByTestId('laboratory-result').scrollIntoViewIfNeeded();
  await settleMotion(page);
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
  await page.screenshot({ path: path.join(output, 'mobile-laboratory-secondary.png') });
  await page.close();
}

async function runDocumentReview(browser, pageErrors) {
  const page = await browser.newPage({ viewport: { width: 1440, height: 950 }, acceptDownloads: true });
  page.on('pageerror', (error) => pageErrors.push(error.message));
  await page.goto(`${baseUrl}/?case_id=ELO-1042#governanca`);
  const before = await (await page.request.get(`${baseUrl}/api/state`)).json();
  let form = page.getByTestId('analyze-EVD-0001');
  await form.getByLabel('Responsável pela extração').fill('Analista Documental Demo');
  await form.getByRole('button', { name: 'Extrair texto de EVD-0001', exact: true }).click();
  await page.getByTestId('document-DOC-001').getByText('Identificadores reconhecidos: CTR-1042, FOR-042.', { exact: true }).waitFor();
  await page.getByRole('heading', { name: 'Ler texto extraído · DOC-001', exact: true }).click();
  await page.getByTestId('document-DOC-001').getByTestId('document-text').getByText(/esmeralda <b>literal<\/b>/).waitFor();
  assert.equal(await page.getByTestId('document-DOC-001').locator('b').count(), 0, 'Texto extraído deve ser escapado');
  await page.getByTestId('document-DOC-001').getByTestId('document-text').scrollIntoViewIfNeeded();
  await settleMotion(page);
  await page.screenshot({ path: path.join(output, 'desktop-document-review.png') });
  form = page.getByTestId('document-review-DOC-001');
  await choose(form.locator('p-select[name=outcome]'), 'Aceitar texto como fonte');
  await form.getByLabel('Li o texto extraído, conferi o documento e os limites desta extração').check();
  await form.getByLabel('Responsável pelo registro').fill('Revisora Documental Demo');
  await form.getByLabel('Justificativa do registro').fill('Trecho literal conferido com o arquivo sintético do contrato.');
  await form.getByRole('button', { name: 'Registrar revisão do texto', exact: true }).click();
  await page.getByTestId('document-DOC-001').locator('.document-status').getByText('Texto aceito', { exact: true }).waitFor();
  await page.goto(`${baseUrl}/?case_id=ELO-1042#inteligencia`);
  form = page.getByTestId('assistant-form');
  await form.getByLabel('Pergunta sobre este caso').fill('esmeralda');
  await form.getByLabel('Responsável pela consulta').fill('Consultora Documental Demo');
  await form.getByRole('button', { name: 'Consultar fontes do caso', exact: true }).click();
  const queryId = `ASK-${String(before.assistant_queries.length + 1).padStart(3, '0')}`;
  await page.getByTestId(`assistant-${queryId}`).getByTestId('assistant-claims').getByText('Fontes: EVD-0001', { exact: true }).waitFor();
  if (aiMode === 'real') {
    form = page.getByTestId('assistant-form');
    await form.getByLabel('Pergunta sobre este caso').fill('Qual verificação esmeralda é descrita no texto revisado e quais identificadores estão mencionados?');
    await form.getByLabel('Responsável pela consulta').fill('Consultora IA Documental Demo');
    await choose(page.locator('#assistant-mode'), 'IA real (requer configuração)');
    await form.getByRole('button', { name: 'Consultar fontes do caso', exact: true }).click();
    const realQueryId = `ASK-${String(before.assistant_queries.length + 2).padStart(3, '0')}`;
    await page.getByTestId(`assistant-${realQueryId}`).waitFor({ timeout: 120000 });
    const saved = (await (await page.request.get(`${baseUrl}/api/state`)).json()).assistant_queries.at(-1);
    assert.equal(saved.mode, 'real');
    assert.equal(saved.abstained, false);
    assert.ok(saved.claims.some((claim) => claim.source_ids.includes('EVD-0001')));
    const rendered = await page.getByTestId(`assistant-${realQueryId}`).getByTestId('assistant-claims').locator('p-text-list-item').allTextContents();
    saved.claims.forEach((claim, index) => claim.source_ids.forEach((id) => assert.ok(rendered[index].includes(id))));
  }
  const after = await (await page.request.get(`${baseUrl}/api/state`)).json();
  for (const key of ['cases', 'risks', 'actions', 'attachments', 'work_items']) assert.deepEqual(after[key], before[key]);
  await page.goto(`${baseUrl}/#governanca`);
  const downloadEvent = page.waitForEvent('download');
  await page.getByRole('link', { name: 'Exportar auditoria de acessos', exact: true }).click();
  const download = await downloadEvent;
  const file = path.join(output, 'access-audit-package.json');
  await download.saveAs(file);
  const exported = JSON.parse(fs.readFileSync(file, 'utf8'));
  assert.equal(exported.format, 'elo-access-audit-v1');
  assert.ok(exported.events.length > 0);
  const verified = require('node:child_process').spawnSync('python3', ['-c', 'import sys,json;sys.path.insert(0,"backend");from access_audit import verify_package;assert verify_package(json.load(open(sys.argv[1])))', file], { encoding: 'utf8' });
  assert.equal(verified.status, 0, verified.stderr);
  await page.close();
  const mobile = await browser.newPage({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
  mobile.on('pageerror', (error) => pageErrors.push(error.message));
  await mobile.goto(`${baseUrl}/?case_id=ELO-1042#governanca`);
  form = mobile.getByTestId('analyze-EVD-0002');
  await form.getByLabel('Responsável pela extração').fill('Analista Mobile Documental');
  await form.getByRole('button', { name: 'Extrair texto de EVD-0002', exact: true }).tap();
  await mobile.getByTestId('document-DOC-002').getByText('Identificadores sem correspondência: FOR-9999.', { exact: true }).waitFor();
  await mobile.getByRole('heading', { name: 'Ler texto extraído · DOC-002', exact: true }).tap();
  await mobile.getByTestId('document-DOC-002').getByTestId('document-text').scrollIntoViewIfNeeded();
  assert.equal(await mobile.evaluate(() => window.unsafeDocument), undefined);
  form = mobile.getByTestId('document-review-DOC-002');
  await choose(form.locator('p-select[name=outcome]'), 'Rejeitar texto');
  await form.getByLabel('Li o texto extraído, conferi o documento e os limites desta extração').check();
  await form.getByLabel('Responsável pelo registro').fill('Revisora Mobile Documental');
  await form.getByLabel('Justificativa do registro').fill('Identificador não corresponde à base sintética deste caso.');
  await form.getByRole('button', { name: 'Registrar revisão do texto', exact: true }).scrollIntoViewIfNeeded();
  await settleMotion(mobile);
  assert.ok(await mobile.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
  await mobile.screenshot({ path: path.join(output, 'mobile-document-review.png') });
  await form.getByRole('button', { name: 'Registrar revisão do texto', exact: true }).tap();
  await mobile.getByTestId('document-DOC-002').locator('.document-status').getByText('Texto rejeitado', { exact: true }).waitFor();
  assert.equal(await mobile.getByTestId('document-review-DOC-002').count(), 0);
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
    await runIndependentWorks(browser, pageErrors);
    await runDesktop(browser, pageErrors);
    await runMobile(browser, pageErrors);
    await runExpanded(browser, pageErrors);
    await runGovernance(browser, pageErrors);
    await runInsights(browser, pageErrors);
    await runAssistant(browser, pageErrors);
    await runWorkUpdates(browser, pageErrors);
    await runRuleConfiguration(browser, pageErrors);
    await runDocumentReview(browser, pageErrors);
    await require('./browser-diagnostic.cjs').runDiagnostic(browser, pageErrors, baseUrl);
    await require('./browser-document-formats.cjs').runDocumentFormats(browser, pageErrors, baseUrl);
    await require('./browser-ocr.cjs').runOCR(browser, pageErrors, baseUrl);
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
