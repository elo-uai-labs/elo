'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const baseUrl = process.env.ELO_URL;
const passwords = JSON.parse(process.env.ELO_TEST_AUTH_PASSWORDS || '{}');
const output = path.resolve('output/validation');
fs.mkdirSync(output, { recursive: true });
const names = { analyst: 'Analista Sintético', reviewer: 'Revisora Sintética', operator: 'Operador Sintético', auditor: 'Auditoria Sintética' };
const errors = [];
const input = (page, selector) => page.locator(selector).locator('input,textarea');
async function choose(control, name) {
  await control.getByRole('combobox').click();
  await control.getByRole('option', { name, exact: true }).click();
}
async function login(page, role, route = '#inteligencia') {
  await page.goto(`${baseUrl}/${route}`);
  await page.getByRole('heading', { name: 'Entrar no Elo', exact: true }).waitFor();
  await input(page, '#login-username').fill(role);
  await input(page, '#login-password').fill(passwords[role]);
  await page.getByRole('button', { name: 'Entrar', exact: true }).click();
  await page.locator('.session-banner').getByText(`${names[role]} · ${role}`, { exact: true }).waitFor();
}
async function typography(page) {
  await page.evaluate(() => document.fonts.ready);
  const properties = await page.locator('#login-password').evaluate((host) => {
    const style = getComputedStyle(host.shadowRoot.querySelector('label'));
    return { family: style.fontFamily, official: getComputedStyle(document.documentElement).getPropertyValue('--p-font-porsche-next') };
  });
  const normalize = (value) => value.replace(/[\s"']/g, '').toLowerCase();
  assert.equal(normalize(properties.family), normalize(properties.official));
  const session = await page.context().newCDPSession(page);
  try {
    await session.send('DOM.enable'); await session.send('CSS.enable');
    const { root } = await session.send('DOM.getDocument', { depth: -1, pierce: true });
    const { nodeId } = await session.send('DOM.querySelector', { nodeId: root.nodeId, selector: '#login-password' });
    const { node } = await session.send('DOM.describeNode', { nodeId, depth: 1, pierce: true });
    const label = await session.send('DOM.querySelector', { nodeId: node.shadowRoots[0].nodeId, selector: 'label' });
    const { fonts } = await session.send('CSS.getPlatformFontsForNode', { nodeId: label.nodeId });
    const drawn = fonts.filter((font) => font.glyphCount > 0);
    assert.ok(drawn.length && drawn.every((font) => font.isCustomFont));
    fs.appendFileSync(path.join(output, 'typography-auth.jsonl'), JSON.stringify({ ...properties, fonts: drawn }) + '\n');
  } finally { await session.detach(); }
}
async function main() {
  const browser = await chromium.launch(process.env.PLAYWRIGHT_CHANNEL ? { channel: process.env.PLAYWRIGHT_CHANNEL } : undefined);
  try {
    const pages = {};
    for (const role of Object.keys(names)) {
      pages[role] = await browser.newPage({ viewport: { width: 1440, height: 950 }, locale: 'pt-BR' });
      pages[role].on('pageerror', (error) => errors.push(error.message));
    }
    const { analyst, reviewer, operator, auditor } = pages;
    await analyst.goto(baseUrl);
    await analyst.getByRole('heading', { name: 'Entrar no Elo', exact: true }).waitFor();
    assert.equal((await analyst.request.get(`${baseUrl}/api/state`)).status(), 401);
    await input(analyst, '#login-username').fill('analyst');
    await input(analyst, '#login-password').fill('wrong-synthetic-password');
    await analyst.getByRole('button', { name: 'Entrar', exact: true }).click();
    await analyst.getByText('Credenciais inválidas.', { exact: true }).waitFor();
    await login(analyst, 'analyst');
    const cookies = await analyst.context().cookies();
    assert.ok(cookies.some((cookie) => cookie.httpOnly && cookie.sameSite === 'Strict'));
    await analyst.getByTestId('detect').click();
    await analyst.getByTestId('evidence-list').waitFor();
    await choose(analyst.locator('#dossier-mode'), 'Síntese local');
    await analyst.getByTestId('generate-dossier').click();
    await analyst.getByTestId('dossier').waitFor();
    assert.equal(await analyst.locator('p-input-text[name=actor]').count(), 0);
    await choose(analyst.locator('#decision-review'), 'Ajustar');
    await choose(analyst.locator('#decision-outcome'), 'Registrar fragilidade');
    await input(analyst, '#decision-reason').fill('Revisão humana autenticada do indício sintético.');
    await analyst.getByTestId('decision-form').locator('input[name=actor]').evaluate((element) => { element.value = 'spoofed-user'; });
    await analyst.getByRole('button', { name: 'Registrar decisão', exact: true }).click();
    await analyst.getByTestId('case-decision').getByText('Fragilidade registrada · analyst', { exact: true }).waitFor();
    let state = await (await analyst.request.get(`${baseUrl}/api/state`)).json();
    assert.equal(state.case.decision.actor, 'analyst');
    assert.equal(state.audit.at(-1).actor, 'analyst');
    assert.deepEqual(state.audit.at(-1).authentication, { mode: 'local-auth', user_id: 'analyst' });
    await analyst.goto(`${baseUrl}/#impactos`);
    await analyst.getByRole('heading', { name: 'Risco e maturidade', exact: true }).waitFor();
    assert.equal(await analyst.locator('form[data-endpoint=impact]').count(), 0);
    assert.equal((await analyst.request.post(`${baseUrl}/api/impact`, { data: { case_id: state.case.id, kind: 'risk', outcome: 'approved', reason: 'Tentativa não permitida.' } })).status(), 403);
    await analyst.goto(`${baseUrl}/#governanca`);
    await input(analyst, '#action-title').fill('Plano atribuído a uma conta de execução');
    await choose(analyst.locator('#action-owner'), 'Operador Sintético · operator');
    await input(analyst, '#action-due').fill('2027-04-15');
    await analyst.getByRole('button', { name: 'Criar plano de ação', exact: true }).click();
    await analyst.getByTestId('action-item').getByText('Plano atribuído a uma conta de execução', { exact: true }).waitFor();
    state = await (await analyst.request.get(`${baseUrl}/api/state`)).json();
    assert.equal(state.actions[0].owner, 'operator');
    assert.equal((await analyst.request.post(`${baseUrl}/api/action/update`, { data: { id: state.actions[0].id, case_id: state.case.id, action_revision: state.actions[0].revision, status: 'in_progress', evidence: '' } })).status(), 403);

    await login(reviewer, 'reviewer', '#impactos');
    for (const kind of ['risk', 'maturity']) {
      const card = reviewer.getByTestId(`impact-${kind}`);
      await choose(card.locator('p-select[name=outcome]'), 'Aprovar');
      await card.getByLabel('Justificativa da avaliação').fill('Revisão independente autenticada do impacto.');
      await card.getByRole('button', { name: 'Registrar avaliação', exact: true }).click();
      await card.getByText('Aprovado', { exact: true }).waitFor();
    }
    await login(operator, 'operator', '#governanca');
    const action = operator.getByTestId('action-item');
    await action.getByRole('heading', { name: 'Atualizar andamento', exact: true }).click();
    await choose(action.locator('p-select[name=status]'), 'Aguardando aprovação de encerramento');
    await action.getByLabel('Evidência de execução').fill('Evidência sintética EXEC-01 registrada pela conta atribuída.');
    await action.getByRole('button', { name: 'Salvar andamento', exact: true }).click();
    await action.locator('.badge').getByText('Aguardando aprovação de encerramento', { exact: true }).waitFor();
    assert.equal(await operator.locator('form[data-endpoint="action/close"]').count(), 0);
    await reviewer.goto(`${baseUrl}/#governanca`);
    const closure = reviewer.locator('form[data-endpoint="action/close"]');
    await choose(closure.locator('p-select[name=outcome]'), 'Aprovar encerramento');
    await closure.getByLabel('Justificativa da revisão').fill('Evidência conferida por conta distinta da execução.');
    await closure.getByRole('button', { name: 'Registrar revisão de encerramento', exact: true }).click();
    await reviewer.getByTestId('action-item').getByText('Concluído', { exact: true }).waitFor();
    state = await (await reviewer.request.get(`${baseUrl}/api/state`)).json();
    assert.equal(state.actions[0].closure_request.actor, 'operator');
    assert.equal(state.actions[0].closure_review.actor, 'reviewer');
    assert.equal(state.audit_valid, true);
    assert.deepEqual(state.audit.at(-1).authentication, { mode: 'local-auth', user_id: 'reviewer' });
    await reviewer.getByTestId('audit-event').getByText('Identidade local autenticada', { exact: true }).first().waitFor();
    await reviewer.screenshot({ path: path.join(output, 'desktop-auth-governance.png'), fullPage: true });

    await login(auditor, 'auditor', '#governanca');
    assert.equal(await auditor.locator('form[data-endpoint="action"]').count(), 0);
    assert.equal((await auditor.request.post(`${baseUrl}/api/detect`, { data: {} })).status(), 403);
    assert.equal((await auditor.request.get(`${baseUrl}/api/audit/export`)).status(), 200);
    await analyst.getByRole('button', { name: 'Sair', exact: true }).click();
    await analyst.getByRole('heading', { name: 'Entrar no Elo', exact: true }).waitFor();
    assert.equal((await analyst.request.get(`${baseUrl}/api/state`)).status(), 401);
    await auditor.context().clearCookies();
    await auditor.getByRole('button', { name: 'Atualizar indicadores de supervisão', exact: true }).click();
    await auditor.getByRole('heading', { name: 'Entrar no Elo', exact: true }).waitFor();
    assert.equal(new URL(auditor.url()).hash, '#governanca');

    const mobile = await browser.newPage({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
    mobile.on('pageerror', (error) => errors.push(error.message));
    await mobile.goto(baseUrl);
    await mobile.locator('p-input-password.hydrated').waitFor();
    await typography(mobile);
    assert.ok(await mobile.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    const native = await mobile.evaluate(() => [...document.querySelectorAll('input:not([type=hidden]),button,select,textarea')].length);
    assert.equal(native, 0, 'Login deve usar somente controles oficiais PDS');
    await mobile.screenshot({ path: path.join(output, 'mobile-auth-login.png'), fullPage: true });
    await login(mobile, 'reviewer', '#governanca');
    await mobile.getByTestId('action-item').getByText('Concluído', { exact: true }).waitFor();
    assert.ok(await mobile.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    await mobile.getByRole('button', { name: 'Sair', exact: true }).tap();
    await mobile.getByRole('heading', { name: 'Entrar no Elo', exact: true }).waitFor();
    for (let attempt = 0; attempt < 5; attempt++) await mobile.request.post(`${baseUrl}/api/login`, { data: { username: 'blocked-fixture', password: 'wrong-synthetic-password' } });
    await input(mobile, '#login-username').fill('blocked-fixture');
    await input(mobile, '#login-password').fill('wrong-synthetic-password');
    await mobile.getByRole('button', { name: 'Entrar', exact: true }).tap();
    await mobile.getByText('Limite de tentativas atingido. Aguarde um minuto.', { exact: true }).waitFor();
    assert.deepEqual(errors, []);
    console.log('Elo auth: quatro perfis, autoria canônica, segregação, atribuição, 401/429, logout e login móvel PDS verificados.');
  } finally { await browser.close(); }
}
main().catch((error) => { console.error(error); process.exitCode = 1; });
