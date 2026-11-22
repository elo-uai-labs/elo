import './styles.css';

const views = {
  visao: 'Visão geral',
  inteligencia: 'Inteligência',
  impactos: 'Risco e maturidade',
  governanca: 'Plano e auditoria',
};

const labels = {
  pending: 'Pendente', detected: 'Detectado', qualified: 'Fragilidade registrada', qualify: 'Registrar fragilidade',
  monitor: 'Em monitoramento', monitored: 'Em monitoramento', monitoring: 'Em monitoramento',
  discard: 'Descartar', discarded: 'Descartado', approved: 'Aprovado', rejected: 'Recusado',
  accept: 'Aceitou a sugestão', adjust: 'Ajustou a sugestão', reject: 'Rejeitou a sugestão',
  open: 'Aberto', in_progress: 'Em andamento', done: 'Concluído', risk: 'Risco', maturity: 'Maturidade',
  low: 'Baixa', medium: 'Média', high: 'Alta', critical: 'Crítica',
  alert_detected: 'Indício detectado', dossier_generated: 'Dossiê gerado', decision_recorded: 'Decisão humana registrada',
  impact_decided: 'Impacto avaliado', action_created: 'Plano de ação criado', action_updated: 'Plano de ação atualizado',
};

const view = document.querySelector('#view');
const notice = document.querySelector('#notice');
let state;
let sending = false;
let selectedCaseId = new URL(location.href).searchParams.get('case_id');

function cases() {
  return state.cases || (state.case ? [state.case] : []);
}

function casePicker() {
  if (!cases().length) return '';
  return `<form class="form case-picker" data-endpoint="select-case" data-testid="case-picker">
    <p-select label="Caso em análise" id="selected-case" name="case_id" value="${escape(state.case?.id)}">
      ${cases().map((item) => `<p-select-option value="${escape(item.id)}">${escape(item.id)} · ${item.decision ? decisionOutcome(item.decision.outcome) : 'Aguardando análise'}</p-select-option>`).join('')}
    </p-select>
    <p-button variant="secondary" icon="none" type="submit">Abrir caso selecionado</p-button>
  </form>`;
}

function escape(value) {
  return String(value ?? '').replace(/[&<>"']/g, (character) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  })[character]);
}

function format(value) {
  return escape(Object.hasOwn(labels, value) ? labels[value] : value);
}

function heading(title, subtitle) {
  return `<header class="page-heading">
    <div class="actions"><p-tag variant="success">Funcional</p-tag><p-tag variant="secondary">Ambiente local · dados sintéticos</p-tag></div>
    <p-heading tag="h1" size="2xl" tabindex="-1">${title}</p-heading>
    <p-text color="contrast-high">${subtitle}</p-text>
  </header>${casePicker()}`;
}

function badge(value) {
  const tones = { pending: 'warning', approved: 'success', done: 'success', qualify: 'success', qualified: 'success', in_progress: 'info' };
  return `<p-tag class="badge" variant="${Object.hasOwn(tones, value) ? tones[value] : 'secondary'}">${format(value)}</p-tag>`;
}

function panel(title, content, extra = '') {
  return `<section class="panel">
    <header class="panel-header"><p-heading tag="h2" size="lg">${title}</p-heading>${extra}</header>
    <div class="panel-content">${content}</div>
  </section>`;
}

function field(id, name, label, type = 'text') {
  const tag = type === 'date' ? 'p-input-date' : 'p-input-text';
  return `<${tag} id="${id}" name="${name}" label="${label}" required></${tag}>`;
}

function paragraph(id, name, label, value = '', required = true) {
  return `<p-textarea id="${id}" name="${name}" label="${label}" value="${escape(value)}" compact${required ? ' required' : ''}></p-textarea>`;
}

function datasetPanel() {
  const { employees, suppliers, contracts } = state.dataset;
  const counts = [['Empregados', employees.length], ['Fornecedores', suppliers.length], ['Contratos', contracts.length]];
  const items = counts.map(([name, count]) => `<div>
    <p-text size="xl" weight="semibold">${escape(count)}</p-text>
    <p-text size="xs" color="contrast-high">${name}</p-text>
  </div>`).join('');
  return panel('Base de demonstração', `<p-text color="contrast-high">Registros fictícios relacionados pela regra de detecção.</p-text>
    <div class="dataset-counts">${items}</div>
    <p-accordion><p-heading slot="summary" tag="h3" size="sm">Consultar registros de origem</p-heading>
      ${[['employees', 'Empregados'], ['suppliers', 'Fornecedores'], ['contracts', 'Contratos']].map(([key, label]) => `<p-heading tag="h4" size="sm">${label}</p-heading><p-text class="technical" size="sm">${escape(JSON.stringify(state.dataset[key], null, 2))}</p-text>`).join('')}
    </p-accordion>
    <p-accordion><p-heading slot="summary" tag="h3" size="sm">Importar base sintética</p-heading>
      <p-text size="sm">Cole um JSON com employees, suppliers e contracts. A importação acrescenta registros, preservando a base e as decisões anteriores. Use identificadores novos e exclusivos; contratos devem referenciar empregados e fornecedores da base ou do novo lote. Depois, execute a análise na Central de inteligência.</p-text>
      <form class="form" data-endpoint="import" data-testid="import-form">
        ${paragraph('import-dataset', 'dataset', 'Base sintética em JSON', JSON.stringify({ employees: [], suppliers: [], contracts: [] }, null, 2))}
        ${field('import-actor', 'actor', 'Responsável pela importação')}
        <p-select label="Origem dos dados" name="synthetic" id="import-synthetic" required><p-select-option value="true">Confirmo que todos os dados são fictícios</p-select-option></p-select>
        <div class="actions"><p-button variant="secondary" icon="none" type="submit">Importar base</p-button></div>
      </form>
    </p-accordion>`);
}

function decisionOutcome(outcome) {
  if (outcome === 'qualify') return 'Fragilidade registrada';
  if (outcome === 'discard') return 'Descartado';
  return format(outcome);
}

function overview() {
  const current = state.case;
  const unreviewed = cases().filter((item) => !item.decision).length;
  const open = state.actions.filter((item) => item.status !== 'done');
  const today = new Date().toLocaleDateString('sv-SE');
  const overdue = open.filter((item) => item.due && item.due < today).length;
  const noImpacts = current?.decision && current.decision.outcome !== 'qualify';
  const stages = [
    ['inteligencia', 'Detecção e dossiê', current?.dossier ? 'Concluído' : 'Pendente'],
    ['inteligencia', 'Decisão humana', current?.decision ? 'Registrada' : 'Pendente'],
    ['impactos', 'Risco e maturidade', noImpacts ? 'Não se aplica' : current?.impacts?.length && current.impacts.every((item) => item.status !== 'pending') ? 'Avaliados' : 'Pendente'],
    ['governanca', 'Plano de ação e auditoria', noImpacts ? 'Decisão auditada' : state.actions.some((item) => item.case_id === current?.id) ? 'Em acompanhamento' : 'Pendente'],
  ];
  const metrics = [['Alertas aguardando análise', unreviewed], ['Criticidade do risco', state.risk.level], ['Recomendações em aberto', open.length], ['Planos de ação atrasados', overdue], ['Maturidade atual', state.maturity.level]];
  const indicators = metrics.map(([name, value]) => `<div class="metric">
    <p-text size="sm" color="contrast-high">${name}</p-text>
    <p-text class="metric-value" size="xl" weight="semibold">${format(value)}</p-text>
  </div>`).join('');
  const journey = stages.map(([route, title, status]) => `<p-text-list-item><div class="journey-step">
    <p-link-pure icon="none" href="#${route}">${title}</p-link-pure>
    <p-tag variant="${['Pendente', 'Não se aplica'].includes(status) ? 'secondary' : 'success'}">${status}</p-tag>
  </div></p-text-list-item>`).join('');
  return `${heading('Visão geral', 'Acompanhe indícios, riscos e decisões em uma trilha única.')}
    <section class="hero" aria-label="Caso de demonstração">
      <div class="hero-copy">
        <p-text size="sm" color="contrast-high">Caso de demonstração</p-text>
        <p-heading tag="h2" size="2xl">Possível conflito de interesses</p-heading>
        <p-text color="contrast-high">Investigue um vínculo cadastral em uma contratação e avalie seus impactos.</p-text>
        <p-link variant="primary" icon="none" href="#inteligencia" data-testid="open-intelligence">${current ? 'Abrir caso' : 'Abrir central de inteligência'}</p-link>
      </div>
      <div class="case-meta">
        <p-text size="sm" color="contrast-high">Situação do caso</p-text>
        <p-text size="md" weight="semibold">${current?.decision ? decisionOutcome(current.decision.outcome) : current ? 'Aguardando revisão humana' : state.detection ? 'Análise concluída sem indícios' : 'Análise ainda não executada'}</p-text>
      </div>
    </section>
    <section class="metric-strip" aria-label="Indicadores de todos os casos">${indicators}</section>
    <div class="grid">${panel(`Jornada do caso${current ? ` · ${escape(current.id)}` : ''}`, `<p-text-list class="record-list" type="numbered">${journey}</p-text-list>`)}${datasetPanel()}</div>`;
}

function evidenceList(current) {
  const items = current.evidence.map((item) => `<p-text-list-item><div class="entry-content">
    <div class="entry-header"><p-text weight="semibold">${escape(item.source)}</p-text><p-tag variant="secondary">${escape(item.id)}</p-tag></div>
    <p-text>${escape(item.detail)}</p-text>
    <p-accordion><p-heading slot="summary" tag="h3" size="sm">Abrir registro ${escape(item.id)}</p-heading>
      <p-text class="technical" size="sm">${escape(JSON.stringify(Object.values(state.dataset).flat().find((record) => record.id === item.id) || { indisponivel: 'Registro não encontrado' }, null, 2))}</p-text>
    </p-accordion>
  </div></p-text-list-item>`).join('');
  return panel('Evidências e fontes', `<p-text size="sm" weight="semibold">Regra aplicada · ${escape(current.rule?.id || 'Vínculo cadastral')} v${escape(current.rule?.version || '1')}</p-text><p-text size="sm">${escape(current.rule?.description || 'Compara o código cadastral não vazio do empregado aprovador com o código do fornecedor relacionado ao contrato. A igualdade indica um vínculo a verificar; não comprova irregularidade.')}</p-text><p-text-list class="record-list" data-testid="evidence-list">${items}</p-text-list>`);
}

function dossierPanel(dossier, decisionExists) {
  const provenance = dossier?.mode === 'real' ? `IA real · ${escape(dossier.model)} · Prompt ${escape(dossier.prompt_version)}` : 'Síntese local baseada nas evidências';
  const content = dossier ? `<p-text size="sm" color="contrast-high">${provenance}</p-text>
    <p-text class="reading" data-testid="dossier">${escape(dossier.text)}</p-text>
    <p-text size="sm" color="contrast-high">Fontes utilizadas: ${dossier.source_ids.map(escape).join(', ')}</p-text>`
    : '<p-text color="contrast-high">Gere o dossiê para revisar a sugestão com as fontes do caso.</p-text>';
  const form = decisionExists ? '' : `<form class="form" data-endpoint="dossier">
    <p-select label="Modo de síntese" id="dossier-mode" name="mode" value="${dossier?.mode || (state.ai_configured ? 'real' : 'local')}">
      <p-select-option value="local">Síntese local</p-select-option>
      <p-select-option value="real">IA real (requer configuração)</p-select-option>
    </p-select>
    <div class="actions"><p-button variant="secondary" icon="none" data-testid="generate-dossier" type="submit">${dossier ? 'Gerar novamente' : 'Gerar dossiê'}</p-button></div>
  </form>`;
  return panel('Dossiê do indício', content + form);
}

function decisionPanel(current) {
  if (current.decision) {
    const saved = current.decision;
    const next = saved.outcome === 'qualify' ? '<div class="actions"><p-link variant="primary" icon="none" href="#impactos">Avaliar impacto em risco e maturidade</p-link></div>' : '';
    return panel('Decisão humana', `<div class="decision-block" data-testid="case-decision">
      <p-text weight="semibold">${decisionOutcome(saved.outcome)} · ${escape(saved.actor)}</p-text>
      <p-text size="sm" color="contrast-high">${format(saved.review)}</p-text>
      <p-text class="reading">${escape(saved.reason)}</p-text>
    </div>${next}`);
  }
  if (!current.dossier) return panel('Decisão humana', '<p-text color="contrast-high">Gere um dossiê antes de registrar a decisão.</p-text>');
  return panel('Decisão humana', `<form class="form" data-endpoint="decision" data-testid="decision-form">
    <input type="hidden" name="dossier_revision" value="${escape(current.dossier.revision)}">
    <div class="form-grid">
      <p-select label="Avaliação da sugestão" id="decision-review" name="review" required>
        <p-select-option value="accept">Aceitar</p-select-option>
        <p-select-option value="adjust">Ajustar</p-select-option>
        <p-select-option value="reject">Rejeitar</p-select-option>
      </p-select>
      <p-select label="Destino do indício" id="decision-outcome" name="outcome" required>
        <p-select-option value="qualify">Registrar fragilidade</p-select-option>
        <p-select-option value="monitor">Manter em monitoramento</p-select-option>
        <p-select-option value="discard">Descartar</p-select-option>
      </p-select>
    </div>
    ${field('decision-actor', 'actor', 'Analista responsável')}
    ${paragraph('decision-reason', 'reason', 'Justificativa')}
    <div class="actions"><p-button variant="primary" icon="none" type="submit">Registrar decisão</p-button></div>
  </form>`);
}

function detectionPanel() {
  const lastDetection = state.audit.findLast((event) => Array.isArray(event.details.case_ids));
  const noNewMatches = lastDetection && lastDetection.details.case_ids.length === 0;
  const pending = state.dataset.contracts.filter((item) => !(state.detection?.processed_contract_ids || []).includes(item.id)).length;
  return panel('Detecção de indícios', `<p-text>${state.detection ? `${cases().length} indício(s) detectado(s). ${pending} contrato(s) ainda não analisado(s).` : 'Execute a regra de cruzamento da base sintética de contratação.'}</p-text>
    ${noNewMatches ? '<p-inline-notification state="success" heading="Análise concluída sem novos indícios" description="Nenhum contrato do último lote analisado apresentou igualdade entre os códigos cadastrais do aprovador e do fornecedor. Esse resultado não comprova ausência de outros riscos." dismiss-button="false"></p-inline-notification>' : ''}
    <form class="form" data-endpoint="detect"><div class="actions"><p-button variant="primary" icon="none" data-testid="detect" type="submit"${state.detection && !pending ? ' disabled' : ''}>Executar análise</p-button></div></form>`);
}

function intelligence() {
  const title = heading('Central de inteligência', 'Revise o vínculo identificado, consulte as fontes e registre a decisão humana.');
  const current = state.case;
  if (!current) return `${title}<div class="grid">${detectionPanel()}${datasetPanel()}</div>`;
  const caseSummary = panel(`Possível conflito de interesses · ${escape(current.id)}`, '<p-text>O vínculo cadastral requer revisão humana. As evidências não demonstram, por si só, uma irregularidade.</p-text>', badge(current.status));
  return `${title}<div class="grid">
    <div class="stack">${caseSummary}${dossierPanel(current.dossier, Boolean(current.decision))}${decisionPanel(current)}</div>
    <div class="stack">${evidenceList(current)}${detectionPanel()}${datasetPanel()}</div>
  </div>`;
}

function impactCard(item) {
  const { kind, label, status, actor, reason } = item;
  const prefix = `impact-${escape(kind)}`;
  const grounding = `<div class="entry-header">
    <p-link-pure icon="none" href="#inteligencia">Caso ${escape(item.case_id)}</p-link-pure>
    <p-text size="sm" color="contrast-high">Evidências ${item.source_ids.map(escape).join(', ')}</p-text>
  </div>
  <p-text size="lg" weight="semibold">${escape(item.current_level)} → ${escape(item.proposed_level)}</p-text>
  <p-text class="reading">${escape(item.rationale)}</p-text>`;
  const decision = status !== 'pending'
    ? `<p-text class="reading" size="sm" color="contrast-high">${escape(actor)} · ${escape(reason)}</p-text>`
    : `<form class="form" data-endpoint="impact">
      <input type="hidden" name="kind" value="${escape(kind)}">
      <div class="form-grid">
        <p-select label="Decisão sobre ${kind === 'risk' ? 'risco' : 'maturidade'}" id="${prefix}-outcome" name="outcome" required>
          <p-select-option value="approved">Aprovar</p-select-option><p-select-option value="rejected">Recusar</p-select-option>
        </p-select>
        ${field(`${prefix}-actor`, 'actor', 'Responsável pela avaliação')}
      </div>
      ${paragraph(`${prefix}-reason`, 'reason', 'Justificativa da avaliação')}
      <div class="actions"><p-button variant="primary" icon="none" type="submit">Registrar avaliação</p-button></div>
    </form>`;
  return `<p-text-list-item data-testid="${prefix}"><div class="entry-content">
    <div class="entry-header"><p-text weight="semibold">${format(kind)} · ${escape(label)}</p-text>${badge(status)}</div>
    ${grounding}${decision}
  </div></p-text-list-item>`;
}

function impacts() {
  const current = state.case;
  const controls = state.risk.controls.map((item) => `<p-text-list-item>${escape(item)}</p-text-list-item>`).join('');
  const risk = panel('Risco associado', `<p-text weight="semibold">${escape(state.risk.name)}</p-text>
    <p-text size="sm" color="contrast-high">Criticidade atual: ${format(state.risk.level)}</p-text>
    <p-divider></p-divider><p-text weight="semibold">Controles vinculados</p-text><p-text-list>${controls}</p-text-list>`);
  const maturity = panel('Maturidade', `<p-text weight="semibold">${escape(state.maturity.name)}</p-text>
    <p-text size="sm" color="contrast-high">Nível atual: ${format(state.maturity.level)}</p-text>
    <p-text size="sm" color="contrast-high">Metodologia ilustrativa para a demonstração.</p-text>`);
  const proposals = current?.impacts?.length
    ? `<p-text-list class="record-list">${current.impacts.map(impactCard).join('')}</p-text-list><div class="actions"><p-link variant="secondary" icon="none" href="#governanca">Abrir plano e auditoria</p-link></div>`
    : '<p-text color="contrast-high">As propostas são geradas quando um analista registra uma fragilidade.</p-text><div class="actions"><p-link variant="secondary" icon="none" href="#inteligencia">Abrir central de inteligência</p-link></div>';
  return `${heading('Risco e maturidade', 'Avalie cada impacto proposto a partir da fragilidade qualificada.')}
    <div class="grid">${panel('Impactos propostos', proposals)}<div class="stack">${risk}${maturity}</div></div>`;
}

function actionForm() {
  if (state.case?.decision?.outcome !== 'qualify') return '<p-text color="contrast-high">Registre uma fragilidade para criar um plano de ação.</p-text>';
  return `<form class="form" data-endpoint="action" data-testid="action-form">
    ${field('action-title', 'title', 'Recomendação')}
    <div class="form-grid">${field('action-owner', 'owner', 'Pessoa responsável')}${field('action-due', 'due', 'Prazo', 'date')}</div>
    ${field('action-actor', 'actor', 'Quem está registrando')}
    <div class="actions"><p-button variant="primary" icon="none" type="submit">Criar plano de ação</p-button></div>
  </form>`;
}

function actionCard(item) {
  const prefix = `action-${escape(item.id)}`;
  const options = ['open', 'in_progress', 'done'].map((status) => `<p-select-option value="${status}">${format(status)}</p-select-option>`).join('');
  return `<p-text-list-item data-testid="action-item"><div class="entry-content">
    <div class="entry-header"><p-text weight="semibold">${escape(item.title)}</p-text>${badge(item.status)}</div>
    <p-text size="sm" color="contrast-high">Caso ${escape(item.case_id)} · ${escape(item.owner)} · Prazo ${escape(item.due)}</p-text>
    ${item.evidence ? `<p-text class="reading">Evidência: ${escape(item.evidence)}</p-text>` : ''}
    <p-accordion><p-heading slot="summary" tag="h3" size="sm">Atualizar andamento</p-heading><form class="form" data-endpoint="action/update">
      <input type="hidden" name="id" value="${escape(item.id)}"><input type="hidden" name="case_id" value="${escape(item.case_id)}">
      <div class="form-grid">
        <p-select label="Situação" id="${prefix}-status" name="status" value="${escape(item.status)}">${options}</p-select>
        ${field(`${prefix}-actor`, 'actor', 'Quem está registrando')}
      </div>
      ${paragraph(`${prefix}-evidence`, 'evidence', 'Evidência de execução', item.evidence, false)}
      <div class="actions"><p-button variant="secondary" icon="none" type="submit">Salvar andamento</p-button></div>
    </form></p-accordion>
  </div></p-text-list-item>`;
}

function auditEvent(event) {
  const time = new Date(event.at);
  const timestamp = Number.isFinite(time.valueOf()) ? time.toLocaleString('pt-BR') : event.at;
  return `<p-text-list-item data-testid="audit-event"><div class="entry-content">
    <p-text weight="semibold">${escape(event.seq)} · ${format(event.action)}</p-text>
    <p-text color="contrast-high" size="sm">${escape(event.actor)} · ${escape(timestamp)}</p-text>
    <p-accordion><p-heading slot="summary" tag="h3" size="sm">Detalhes e hash</p-heading>
      <p-text class="technical" size="sm">${escape(JSON.stringify(event.details, null, 2))}</p-text>
      <p-text class="technical" color="contrast-high" size="sm">${escape(event.hash)}</p-text>
    </p-accordion>
  </div></p-text-list-item>`;
}

function supervision(current) {
  if (!current?.dossier || !current.decision) return '<p-text color="contrast-high">A sugestão e a decisão final aparecem lado a lado após a revisão humana.</p-text>';
  return `<div class="split-review" data-testid="supervision">
    <div class="decision-block">
      <p-heading tag="h3" size="md">${current.dossier.mode === 'real' ? 'Sugestão da IA' : 'Síntese local revisada'}</p-heading>
      <p-text class="reading">${escape(current.dossier.text)}</p-text>
    </div>
    <div class="decision-block">
      <p-heading tag="h3" size="md">Decisão e justificativa</p-heading>
      <p-text weight="semibold">${decisionOutcome(current.decision.outcome)} · ${escape(current.decision.actor)}</p-text>
      <p-text size="sm" color="contrast-high">${format(current.decision.review)}</p-text>
      <p-text class="reading">${escape(current.decision.reason)}</p-text>
    </div>
  </div>`;
}

function governance() {
  const status = state.audit_valid ? '<p-tag variant="success">Integridade verificada</p-tag>' : '<p-tag variant="error">Falha de integridade</p-tag>';
  const eventList = state.audit.length ? `<p-text-list class="record-list audit">${[...state.audit].reverse().map(auditEvent).join('')}</p-text-list>` : '<p-text color="contrast-high">Nenhum evento registrado.</p-text>';
  const actions = state.actions.length ? `<p-text-list class="record-list">${state.actions.map(actionCard).join('')}</p-text-list>` : '<p-text color="contrast-high">Nenhum plano de ação registrado.</p-text>';
  return `${heading('Plano de ação e auditoria', 'Acompanhe recomendações e consulte quem decidiu o quê, quando e por quê.')}
    <div class="grid"><div class="stack">${panel('Plano de ação', `${actions}${actionForm()}`)}${panel('Supervisão humana', supervision(state.case))}</div>${panel('Trilha de auditoria', '<div class="actions"><p-link variant="secondary" icon="none" href="/api/audit/export" download="elo-auditoria.json">Exportar pacote de auditoria</p-link></div><p-text size="sm" color="contrast-high">Pacote JSON dos registros sintéticos locais, com trilha e hashes SHA-256 para verificação independente de integridade. Não equivale a uma assinatura digital.</p-text>' + eventList, status)}</div>`;
}

function render() {
  const current = location.hash.slice(1);
  const route = Object.hasOwn(views, current) ? current : 'visao';
  const pages = { visao: overview, inteligencia: intelligence, impactos: impacts, governanca: governance };
  document.title = `${views[route]} | Elo`;
  document.querySelector('p-tabs-bar').setAttribute('active-tab-index', Object.keys(views).indexOf(route));
  if (state) view.innerHTML = `<div class="page">${pages[route]()}</div>`;
  view.setAttribute('aria-busy', String(sending));
}

async function read(url, payload) {
  const options = payload ? {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
  } : {};
  const response = await fetch(url, options);
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || 'Não foi possível concluir a operação.');
  return result;
}

function announce(message, error = false) {
  notice.hidden = !message;
  notice.innerHTML = message ? `<p-inline-notification state="${error ? 'error' : (sending ? 'info' : 'success')}" heading="${escape(message)}" dismiss-button="false"></p-inline-notification>` : '';
}

view.addEventListener('update', (event) => {
  if (event.target.matches('p-accordion')) event.target.open = event.detail.open;
}, { capture: true });

document.querySelector('.skip p-link-pure').addEventListener('click', (event) => {
  event.preventDefault();
  document.querySelector('#conteudo').focus();
});

view.addEventListener('submit', async (event) => {
  const form = event.target.closest('form[data-endpoint]');
  if (!form) return;
  event.preventDefault();
  if (sending) return;
  sending = true;
  view.setAttribute('aria-busy', 'true');
  const buttons = [...view.querySelectorAll('p-button[type="submit"]')].map((button) => [button, button.disabled]);
  buttons.forEach(([button]) => { button.disabled = true; });
  announce('Processando…');
  try {
    const endpoint = form.getAttribute('data-endpoint');
    const payload = Object.fromEntries(new FormData(form));
    if (endpoint === 'select-case') {
      state = await read(`/api/state?case_id=${encodeURIComponent(payload.case_id)}`);
    } else {
      if (endpoint === 'import') {
        try { payload.dataset = JSON.parse(payload.dataset); }
        catch { throw new Error('A base deve conter um JSON válido. Revise o conteúdo antes de importar.'); }
        payload.synthetic = payload.synthetic === 'true';
      } else if (state.case && !payload.case_id) payload.case_id = state.case.id;
      state = await read(`/api/${endpoint}`, payload);
    }
    selectedCaseId = state.case?.id || null;
    const url = new URL(location.href);
    if (selectedCaseId) url.searchParams.set('case_id', selectedCaseId);
    else url.searchParams.delete('case_id');
    history.replaceState(null, '', url);
    sending = false;
    announce(form.getAttribute('data-endpoint') === 'select-case' ? 'Caso selecionado.' : 'Registro atualizado.');
    render();
    view.querySelector('p-heading[tag=h1]')?.focus({ preventScroll: true });
  } catch (error) {
    announce(error.message, true);
  } finally {
    sending = false;
    view.setAttribute('aria-busy', 'false');
    buttons.forEach(([button, disabled]) => { button.disabled = disabled; });
  }
});

window.addEventListener('hashchange', () => {
  if (location.hash === '#conteudo') return;
  announce('');
  render();
  window.scrollTo(0, 0);
  view.querySelector('p-heading[tag=h1]')?.focus({ preventScroll: true });
});

async function initialize() {
  try {
    state = await read(`/api/state${selectedCaseId ? `?case_id=${encodeURIComponent(selectedCaseId)}` : ''}`);
    render();
  } catch (error) {
    announce(error.message, true);
    view.innerHTML = '<p-text color="contrast-high">Recarregue a página para tentar se conectar novamente.</p-text>';
    view.setAttribute('aria-busy', 'false');
  }
}

initialize();
