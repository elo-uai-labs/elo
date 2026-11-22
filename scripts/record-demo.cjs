const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs/promises');
const { chromium } = require('playwright');
const base = process.env.ELO_URL;
const work = process.env.ELO_VIDEO_DIR;
if (!work || !base) throw new Error('ELO_VIDEO_DIR e ELO_URL são obrigatórios. Use um banco separado.');
const justification = 'A coincidência cadastral justifica investigar a origem do vínculo. Ela não comprova irregularidade.';

async function run() {
  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 },
    locale: 'pt-BR',
    recordVideo: { dir: work, size: { width: 1280, height: 800 } }
  });
  const page = await context.newPage();
  const recording = page.video();
  const errors = [];
  const beats = [];
  const started = Date.now();
  page.on('pageerror', error => errors.push(error.message));
  const choose = async (control, label) => {
    await control.getByRole('combobox').click();
    await control.getByRole('option', {name:label,exact:true}).click();
  };
  const fill = (selector, value) => page.locator(selector).locator('input, textarea').fill(value);
  const hold = ms => page.waitForTimeout(ms);
  const focus = async locator => {
    await locator.evaluate(el => el.scrollIntoView({ block: 'center', behavior: 'instant' }));
    await hold(250);
  };
  const chapter = async (number, label, copy) => {
    beats.push({ number, started: (Date.now() - started) / 1000 });
    await page.evaluate(({number, label, copy}) => {
      document.querySelector('#elo-video-number').textContent = number;
      document.querySelector('#elo-video-label').textContent = label;
      document.querySelector('#elo-video-copy').textContent = copy;
    }, {number, label, copy});
  };
  try {
    await page.goto(base);
    await page.getByRole('heading', { name: 'Visão geral', exact: true }).waitFor();
    await page.evaluate(() => document.fonts.ready);
    await page.evaluate(() => {
      const bar = document.createElement('aside');
      bar.setAttribute('aria-label', 'Legenda da demonstração');
      Object.assign(bar.style, {
        position: 'fixed', bottom: '0', left: '0', width: '100%', minHeight: '60px',
        display: 'flex', alignItems: 'center', gap: 'var(--p-spacing-static-md)',
        padding: 'var(--p-spacing-static-sm) var(--p-spacing-static-md)',
        boxSizing: 'border-box', colorScheme: 'dark',
        background: 'var(--p-color-canvas)', color: 'var(--p-color-primary)',
        zIndex: '10000', pointerEvents: 'none',
        borderTop: '1px solid var(--p-color-contrast-lower)'
      });
      for (const id of ['number', 'label', 'copy']) {
        const text = document.createElement('p-text');
        text.id = 'elo-video-' + id;
        text.setAttribute('size', 'sm');
        if (id !== 'copy') text.setAttribute('weight', 'semibold');
        bar.append(text);
      }
      document.body.append(bar);
      document.body.style.paddingBottom = '80px';
    });
    await chapter('ELO', 'Radar de Integridade', 'Um caso sintético, da detecção ao plano de ação.');
    await page.locator('p-tabs-bar.hydrated').waitFor();
    await page.screenshot({path: path.join(work, 'overview.png')});
    await hold(3000);
    await page.getByTestId('open-intelligence').click();
    await page.getByTestId('detect').waitFor();
    await chapter('01', 'Detecção', 'O Elo cruza empregados, fornecedores e contratos.');
    await hold(1500);
    await page.getByTestId('detect').click();
    await page.getByTestId('evidence-list').getByRole('listitem').first().waitFor();
    await focus(page.getByTestId('evidence-list'));
    await hold(2800);

    await chapter('02', 'IA real no Mac', 'A síntese usa as evidências do caso e cita suas fontes.');
    await choose(page.locator('#dossier-mode'), 'IA real (requer configuração)');
    await hold(900);
    const pendingDossier = page.waitForResponse(res => res.url().endsWith('/api/dossier'), {timeout:55000});
    await page.getByTestId('generate-dossier').click();
    const response = await pendingDossier;
    if (!response.ok()) throw new Error('IA respondeu HTTP ' + response.status() + ' ' + await response.text());
    await page.getByText(/^IA real · Apple Foundation Models/).waitFor({ timeout: 50000 });
    await focus(page.getByTestId('dossier'));
    await hold(5000);

    await chapter('03', 'Decisão humana', 'O analista ajusta a sugestão, qualifica a fragilidade e justifica.');
    const form = page.getByTestId('decision-form');
    await focus(form);
    await choose(page.locator('#decision-review'), 'Ajustar');
    await hold(450);
    await choose(page.locator('#decision-outcome'), 'Registrar fragilidade');
    await hold(450);
    await fill('#decision-actor', 'Lia Demo');
    await fill('#decision-reason', justification);
    await hold(2700);
    await page.getByRole('button', { name: 'Registrar decisão' }).click();
    await page.getByTestId('case-decision').getByText('Ajustou a sugestão', { exact:true }).waitFor();
    await focus(page.getByTestId('case-decision'));
    await hold(2400);

    await page.getByRole('link', { name:'Avaliar impacto em risco e maturidade' }).click();
    await chapter('04', 'Risco e maturidade', 'Cada impacto proposto exige uma avaliação própria.');
    const decide = async (kind, outcome, reason) => {
      const key = 'impact-' + kind;
      const card = page.getByTestId(key);
      await focus(card);
      await choose(page.locator('#' + key + '-outcome'), outcome === 'approved' ? 'Aprovar' : 'Recusar');
      await fill('#' + key + '-actor', 'Rita Demo');
      await fill('#' + key + '-reason', reason);
      await hold(1000);
      await card.getByRole('button', { name:'Registrar avaliação' }).click();
      await card.getByText(outcome === 'approved' ? 'Aprovado' : 'Recusado', { exact:true }).waitFor();
    };
    await decide('risk','approved','O vínculo merece reavaliação dos controles de contratação.');
    await decide('maturity','rejected','A amostra é insuficiente para alterar a maturidade.');
    await focus(page.getByTestId('impact-maturity'));
    await hold(2900);

    await page.getByRole('link', { name:'Abrir plano e auditoria' }).click();
    await chapter('05', 'Plano de ação', 'A recomendação ganha responsável, prazo e evidência de execução.');
    await focus(page.getByTestId('action-form'));
    await fill('#action-title', 'Verificar a origem do vínculo cadastral');
    await fill('#action-owner', 'Marco Demo');
    await fill('#action-due', '2027-01-15');
    await fill('#action-actor', 'Lia Demo');
    await hold(2100);
    await page.getByRole('button', { name:'Criar plano de ação' }).click();
    const action = page.getByTestId('action-item');
    await action.getByText('Verificar a origem do vínculo cadastral', { exact:true }).waitFor();
    await action.getByText('Atualizar andamento', { exact:true }).click();
    await choose(action.locator('p-select[name=status]'), 'Concluído');
    await action.getByLabel('Quem está registrando').fill('Marco Demo');
    await action.getByLabel('Evidência de execução').fill('Ata sintética DEMO-01.');
    await hold(1100);
    await action.getByRole('button', { name:'Salvar andamento' }).click();
    await action.locator('.badge').getByText('Concluído', { exact:true }).waitFor();
    await hold(1650);

    await chapter('06', 'Auditoria', 'A sugestão da IA e a decisão justificada ficam lado a lado.');
    const supervision = page.getByTestId('supervision');
    await supervision.getByText('Sugestão da IA', { exact:true }).waitFor();
    await supervision.getByText(justification, { exact:true }).waitFor();
    await page.getByText('Integridade verificada', { exact:true }).waitFor();
    await focus(supervision);
    await hold(6000);
    const state = await (await fetch(base + '/api/state')).json();
    assert.equal(state.case.dossier.mode, 'real');
    assert.match(state.case.dossier.model, /Apple Foundation Models/);
    assert.ok(state.case.dossier.source_ids.length);
    assert.equal(state.case.decision.dossier_revision, state.case.dossier.revision);
    assert.equal(state.case.decision.review, 'adjust');
    assert.deepEqual(state.case.impacts.map(item => item.status), ['approved','rejected']);
    assert.equal(state.actions[0].status, 'done');
    assert.equal(state.audit_valid, true);
    assert.deepEqual(errors, []);
    await page.screenshot({ path: path.join(work, 'auditoria.png') });
    await page.getByRole('navigation', {name:'Módulos do Elo'}).getByRole('link', {name:'Visão geral',exact:true}).click();
    await page.getByRole('heading', {name:'Visão geral',exact:true}).waitFor();
    await chapter('ELO', 'Fluxo concluído', 'Decisões salvas. Indicadores atualizados. Trilha verificada.');
    await hold(3500);
    await fs.writeFile(path.join(work,'evidence.json'), JSON.stringify({ beats, duration: (Date.now()-started)/1000, promptVersion:state.case.dossier.prompt_version, model:state.case.dossier.model, sources:state.case.dossier.source_ids, auditEvents:state.audit.length }, null, 2));
  } finally {
    await context.close();
    await recording.saveAs(path.join(work,'captura.webm'));
    await browser.close();
  }
}
run().catch(error => { console.error(error); process.exitCode=1; });
