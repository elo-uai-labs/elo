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
  open: 'Aberto', in_progress: 'Em andamento', done: 'Concluído', draft: 'Rascunho', closure_requested: 'Aguardando aprovação de encerramento', risk: 'Risco', maturity: 'Maturidade',
  low: 'Baixa', medium: 'Média', high: 'Alta', critical: 'Crítica',
  alert_detected: 'Indício detectado', dossier_generated: 'Dossiê gerado', decision_recorded: 'Decisão humana registrada',
  impact_decided: 'Impacto avaliado', action_created: 'Plano de ação criado', action_updated: 'Plano de ação atualizado',
};

const view = document.querySelector('#view');
const notice = document.querySelector('#notice');
let state;
let session;
let people = [];
const selectedFiles = new Map();
let sending = false;
let laboratoryResult;
let supervisionResult;
let insights;
let insightsError = '';
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

const roleLabels = { admin: 'Administração', analyst: 'Análise', reviewer: 'Revisão', operator: 'Execução', auditor: 'Consulta e auditoria' };

function sessionBanner() {
  if (!session?.authenticated) return '';
  return `<div class="panel session-banner"><div class="entry-content"><p-text weight="semibold">${escape(session.user.name)} · ${escape(session.user.id)}</p-text>
    <p-text size="sm">Conta local · ${session.user.roles.map((role) => escape(roleLabels[role] || role)).join(', ')}</p-text></div>
    <form data-endpoint="logout"><p-button variant="secondary" icon="none" type="submit">Sair</p-button></form></div>`;
}

function loginScreen() {
  return `<div class="page"><header class="page-heading"><p-tag variant="secondary">Ambiente local · dados sintéticos</p-tag>
    <p-heading tag="h1" size="2xl">Entrar no Elo</p-heading><p-text color="contrast-high">Use sua conta local para acessar os casos e as ações permitidas ao seu perfil.</p-text></header>
    ${panel('Acesso identificado', `<form class="form" data-endpoint="login" data-testid="login-form">
      <p-input-text id="login-username" name="username" label="Identificador da conta" autocomplete="username" required></p-input-text>
      <p-input-password id="login-password" name="password" label="Senha" autocomplete="current-password" toggle required></p-input-password>
      <div class="actions"><p-button variant="primary" icon="none" type="submit">Entrar</p-button></div>
    </form><p-text size="sm" color="contrast-high">Contas provisionadas pelo administrador deste ambiente. Esta autenticação local não representa integração com o provedor corporativo da CAIXA.</p-text>`)}
  </div>`;
}

function permissionReason(endpoint, form) {
  if (!session?.auth_required || ['select-case', 'laboratory/run', 'supervision/read', 'insights/read', 'assistant/query', 'logout'].includes(endpoint)) return '';
  const user = session.user;
  if (!user) return 'Entre para continuar.';
  const roles = user.roles;
  const analyst = ['import', 'detect', 'dossier', 'decision', 'case/link', 'action', 'report/create', 'scenario/create'];
  const reviewer = ['risk/save', 'control/save', 'dimension/save', 'catalog/archive', 'maturity/assess', 'impact', 'action/edit', 'action/close', 'report/review', 'scenario/create'];
  const uploadActionId = form.querySelector('input[name=action_id]')?.value;
  const uploadAllowed = endpoint === 'evidence/upload' && (uploadActionId ? roles.some((role) => ['operator', 'analyst', 'admin'].includes(role)) : roles.some((role) => ['analyst', 'reviewer', 'admin'].includes(role)));
  const permitted = uploadAllowed || roles.includes('admin') || (analyst.includes(endpoint) && roles.includes('analyst')) ||
    (reviewer.includes(endpoint) && roles.includes('reviewer')) || (endpoint === 'action/update' && roles.some((role) => ['operator', 'analyst'].includes(role)));
  if (!permitted) return 'Seu perfil permite consultar esta área, mas não executar esta ação.';
  if (endpoint === 'evidence/upload' && uploadActionId && state.actions.find((item) => item.id === uploadActionId)?.owner !== user.id) return 'Somente o responsável atribuído ao plano pode anexar evidências de execução.';
  if (endpoint === 'report/review' && state.reports?.find((item) => item.id === form.querySelector('input[name=id]')?.value)?.creator === user.id) return 'A revisão do relatório exige outra pessoa, diferente de quem o compilou.';
  if (endpoint === 'impact' && state.case?.decision?.actor === user.id) return 'A avaliação de impacto exige outro revisor, diferente de quem qualificou o caso.';
  const id = form.querySelector('input[name=id]')?.value;
  const action = state.actions.find((item) => item.id === id);
  if (endpoint === 'action/update' && action?.owner !== user.id) return 'Somente o responsável atribuído ao plano pode registrar a execução.';
  if (endpoint === 'action/close' && action?.closure_request?.actor === user.id) return 'A revisão do encerramento exige outra pessoa.';
  return '';
}

async function loadWorkspace() {
  const [nextState, directory] = await Promise.all([
    read(`/api/state${selectedCaseId ? `?case_id=${encodeURIComponent(selectedCaseId)}` : ''}`),
    session.auth_required ? read('/api/people') : Promise.resolve({ people: [] }),
  ]);
  state = nextState;
  people = directory.people;
  await refreshInsights();
}

function expiredSession(error) {
  if (error.status !== 401 || !session?.auth_required) return false;
  session = { ...session, authenticated: false, user: null };
  state = undefined;
  people = [];
  selectedFiles.clear();
  insights = undefined;
  insightsError = '';
  supervisionResult = undefined;
  laboratoryResult = undefined;
  render();
  return true;
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

function field(id, name, label, type = 'text', value = '') {
  if (name === 'actor' && session?.authenticated) return `${hidden('actor', session.user.id)}<p-text size="sm">${escape(label)}: ${escape(session.user.name)} · ${escape(session.user.id)} (conta autenticada)</p-text>`;
  if (name === 'owner' && session?.auth_required) return selectField(id, name, label, people.filter((person) => person.roles.some((role) => ['operator', 'analyst', 'admin'].includes(role))).map((person) => [person.id, `${person.name} · ${person.id}`]), value);
  const tag = type === 'date' ? 'p-input-date' : 'p-input-text';
  return `<${tag} id="${id}" name="${name}" label="${label}" value="${escape(value)}" required></${tag}>`;
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

async function refreshInsights() {
  if (!state) return;
  try {
    insights = await read(`/api/insights${state.case ? `?case_id=${encodeURIComponent(state.case.id)}` : ''}`);
    insightsError = '';
  } catch (error) {
    insights = undefined;
    insightsError = error.message;
    if (error.status === 401) throw error;
  }
}

function insightFeedback() {
  return insightsError ? `<p-inline-notification state="error" heading="Contexto analítico indisponível" description="${escape(insightsError)}" dismiss-button="false"></p-inline-notification><form data-endpoint="insights/read"><p-button variant="secondary" icon="none" type="submit">Atualizar contexto analítico</p-button></form>` : '';
}

function trendsPanel() {
  const trend = insights?.trends;
  const headings = ['Mês', 'Indícios', 'Fragilidades', 'Monitoramentos', 'Descartes', 'Planos concluídos'];
  return panel('Evolução mensal', `${insightFeedback()}${trend ? `<p-text size="sm">${escape(trend.scope)}</p-text><p-text size="sm" color="contrast-high">Fuso de referência: ${escape(trend.timezone)}</p-text>
    ${trend.periods.length ? `<p-table caption="Eventos registrados por mês" data-testid="event-trends"><p-table-head><p-table-head-row>${headings.map((label) => `<p-table-head-cell>${label}</p-table-head-cell>`).join('')}</p-table-head-row></p-table-head><p-table-body>${trend.periods.map((period) => `<p-table-row>${['period', 'detected', 'qualified', 'monitored', 'discarded', 'completed'].map((key) => `<p-table-cell>${escape(period[key])}</p-table-cell>`).join('')}</p-table-row>`).join('')}</p-table-body></p-table>` : '<p-text size="sm">Nenhum evento registrado para compor a evolução mensal.</p-text>'}` : ''}`);
}

function memoryPanel() {
  const memory = insights?.memory;
  return panel('Memória institucional', `${insightFeedback()}${memory ? `<p-text size="sm" color="contrast-high">${escape(memory.methodology)}</p-text>
    ${memory.matches.length ? `<p-text-list class="record-list" data-testid="similar-cases">${memory.matches.map((item) => `<p-text-list-item><div class="entry-content">
      <p-link-pure icon="none" href="?case_id=${encodeURIComponent(item.case_id)}#inteligencia">Abrir ${escape(item.case_id)}</p-link-pure>
      <p-text size="sm">Pontuação de correspondência: ${escape(item.score)} · ${item.reasons.map(escape).join(' · ')}</p-text>
      <p-text weight="semibold">Decisão anterior: ${decisionOutcome(item.decision.outcome)} · ${escape(item.decision.actor)}</p-text><p-text>${escape(item.decision.reason)}</p-text>
    </div></p-text-list-item>`).join('')}</p-text-list>` : '<p-text size="sm">Nenhum outro caso revisado compartilha os critérios de correspondência.</p-text>'}` : '<p-text size="sm">Selecione um caso para consultar decisões anteriores relacionadas.</p-text>'}`);
}

function connectionsPanel() {
  const graph = insights?.connections;
  const label = (id) => {
    const item = graph.nodes.find((node) => node.id === id);
    return `${escape(id)}${item?.label && item.label !== id ? ` · ${escape(item.label)}` : ''}`;
  };
  return panel('Conexões do caso', `${insightFeedback()}${graph ? `<p-text size="sm">${escape(graph.scope)}</p-text>
    <p-text-list class="record-list" data-testid="case-connections">${graph.edges.map((edge) => `<p-text-list-item><div class="entry-content"><p-text weight="semibold">${label(edge.source)} → ${label(edge.target)}</p-text><p-text size="sm" color="contrast-high">${escape(edge.relation)}</p-text></div></p-text-list-item>`).join('')}</p-text-list>` : '<p-text size="sm">Execute uma análise para consultar os registros conectados.</p-text>'}`);
}

function scenarioPanel() {
  const active = (state.risks || []).filter((item) => !item.archived);
  const scenarios = state.scenarios || insights?.scenarios || [];
  return panel('Simulador de cenários', `<p-tag variant="warning">Metodologia ilustrativa</p-tag>
    <p-text>Explore probabilidade e impacto de 1 a 5. O cenário é registrado separadamente e não altera a avaliação vigente do risco.</p-text>
    ${active.length ? `<form class="form" data-endpoint="scenario/create" data-testid="scenario-form">
      ${selectField('scenario-risk', 'risk_id', 'Risco para simular', active.map((item) => [item.id, item.name]), active.some((item) => item.id === state.risk.id) ? state.risk.id : active[0].id)}
      <div class="form-grid"><p-input-number id="scenario-likelihood" name="likelihood" label="Probabilidade" min="1" max="5" step="1" required></p-input-number>
      <p-input-number id="scenario-impact" name="impact" label="Impacto" min="1" max="5" step="1" required></p-input-number></div>
      ${auditFields('scenario')}<div class="actions"><p-button variant="secondary" icon="none" type="submit">Registrar cenário hipotético</p-button></div>
    </form>` : '<p-text size="sm">Cadastre um risco ativo para simular cenários.</p-text>'}
    ${scenarios.length ? `<p-text-list class="record-list">${[...scenarios].reverse().map((scenario) => `<p-text-list-item><div class="entry-content" data-testid="scenario-${escape(scenario.id)}">
      <p-text weight="semibold">${escape(scenario.id)} · ${escape(scenario.risk_id)} · Hipótese ${escape(scenario.hypothetical_level)}</p-text>
      <p-text size="sm">Avaliação vigente no registro: ${escape(scenario.current_level)} · ${scenario.likelihood} × ${scenario.impact} = ${scenario.score}</p-text>
      <p-text>${escape(scenario.reason)} · ${escape(scenario.actor)}</p-text><p-text size="sm">${escape(scenario.methodology)}</p-text><p-text weight="semibold" size="sm">${escape(scenario.effect)}</p-text>
    </div></p-text-list-item>`).join('')}</p-text-list>` : '<p-text size="sm" color="contrast-high">Nenhum cenário hipotético registrado.</p-text>'}`);
}

function integrationPanel() {
  const batches = state.integration_batches || [];
  return panel('Lotes do serviço local', `<p-text size="sm">Importação sintética iniciada explicitamente pela ferramenta local. Estes registros não representam integração com sistemas institucionais.</p-text>
    ${batches.length ? `<p-text-list>${batches.slice(-5).reverse().map((batch) => `<p-text-list-item><div class="entry-content"><p-text weight="semibold">${escape(batch.id)} · ${escape(batch.source_name)}</p-text><p-text size="sm">${escape(batch.at)} · ${escape(batch.actor)} · ${batch.contracts_analyzed} contrato(s) analisado(s) · ${batch.case_ids.length} indício(s)</p-text><p-text size="sm">Importados: ${batch.imported_counts.employees} empregado(s), ${batch.imported_counts.suppliers} fornecedor(es), ${batch.imported_counts.contracts} contrato(s).</p-text><p-text class="technical" size="xs">SHA-256: ${escape(batch.content_sha256)}</p-text></div></p-text-list-item>`).join('')}</p-text-list>` : '<p-text size="sm">Nenhum lote do serviço local registrado.</p-text>'}`);
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
  const distribution = (items, fallback) => {
    const active = items?.filter((item) => !item.archived) || [];
    if (active.length <= 1) return active[0]?.level || fallback;
    const counts = active.reduce((result, item) => ({ ...result, [item.level]: (result[item.level] || 0) + 1 }), {});
    return Object.entries(counts).map(([level, count]) => `${level}: ${count}`).join(' · ');
  };
  const metrics = [['Alertas aguardando análise', unreviewed], ['Riscos por criticidade', distribution(state.risks, state.risk.level)], ['Recomendações em aberto', open.length], ['Planos de ação atrasados', overdue], ['Situação da maturidade', distribution(state.dimensions, state.maturity.level)]];
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
        <p-heading tag="h2" size="2xl">${escape(current?.title || 'Possível conflito de interesses')}</p-heading>
        <p-text color="contrast-high">Investigue um vínculo cadastral em uma contratação e avalie seus impactos.</p-text>
        <p-link variant="primary" icon="none" href="#inteligencia" data-testid="open-intelligence">${current ? 'Abrir caso' : 'Abrir central de inteligência'}</p-link>
      </div>
      <div class="case-meta">
        <p-text size="sm" color="contrast-high">Situação do caso</p-text>
        <p-text size="md" weight="semibold">${current?.decision ? decisionOutcome(current.decision.outcome) : current ? 'Aguardando revisão humana' : state.detection ? 'Análise concluída sem indícios' : 'Análise ainda não executada'}</p-text>
      </div>
    </section>
    <section class="metric-strip" aria-label="Indicadores de todos os casos">${indicators}</section>
    <div class="grid">${panel(`Jornada do caso${current ? ` · ${escape(current.id)}` : ''}`, `<p-text-list class="record-list" type="numbered">${journey}</p-text-list>`)}${datasetPanel()}</div>${trendsPanel()}${integrationPanel()}`;
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
    ${dossier.claims?.length ? `<div class="stack" data-testid="dossier"><p-text-list>${dossier.claims.map((claim) => `<p-text-list-item><p-text>${escape(claim.text)}</p-text><p-text size="sm" color="contrast-high">Fontes: ${claim.source_ids.map(escape).join(', ')}</p-text></p-text-list-item>`).join('')}</p-text-list><p-text class="reading">Limitações: ${escape(dossier.limitations)}</p-text><p-text class="reading">Sugestão: ${escape(dossier.suggestion)}</p-text></div>` : `<p-text class="reading" data-testid="dossier">${escape(dossier.text)}</p-text>`}
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
    ${hidden('linkage_revision', current.linkage_revision)}
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

function laboratoryPanel() {
  const labels = { tp: 'Sinais encontrados corretamente', fp: 'Alarmes falsos', fn: 'Sinais não encontrados', tn: 'Negativos corretos' };
  const result = laboratoryResult;
  return panel('Laboratório sintético', `<p-text size="sm">Execute a regra em uma organização fictícia com gabarito independente. O laboratório não altera os casos desta base.</p-text>
    <form class="form" data-endpoint="laboratory/run"><div class="actions"><p-button variant="secondary" icon="none" type="submit">Executar laboratório sintético</p-button></div></form>
    ${result ? `<div class="stack" data-testid="laboratory-result"><p-text>${escape(result.scope)}</p-text>
      <p-text size="sm">${escape(result.fixture.id)} · Versão ${escape(result.fixture.version)} · ${result.counts.total} contratos</p-text>
      <p-text-list>${Object.entries(labels).map(([key, label]) => `<p-text-list-item>${label}: ${result.counts[key]}</p-text-list-item>`).join('')}</p-text-list>
      <p-text>Precisão: ${ratio(result.metrics.precision.value)} (${result.metrics.precision.numerator}/${result.metrics.precision.denominator}) · Sensibilidade: ${ratio(result.metrics.recall.value)} (${result.metrics.recall.numerator}/${result.metrics.recall.denominator})</p-text>
      <p-accordion><p-heading slot="summary" tag="h3" size="sm">Cenários e gabarito</p-heading><p-text-list>${result.outcomes.map((item) => `<p-text-list-item>${escape(item.contract_id)} · ${escape(item.scenario)} · ${labels[item.outcome]}. ${escape(item.reason)}</p-text-list-item>`).join('')}</p-text-list></p-accordion>
      <p-text class="technical" size="sm">SHA-256 do gabarito: ${escape(result.fixture.sha256)}</p-text></div>` : ''}`);
}

function ratio(value) {
  return value == null ? 'Sem denominador' : `${(value * 100).toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`;
}

function supervisionPanel() {
  const result = supervisionResult;
  return panel('Indicadores de supervisão', `<form class="form" data-endpoint="supervision/read"><div class="actions"><p-button variant="secondary" icon="none" type="submit">Atualizar indicadores de supervisão</p-button></div></form>
    ${result ? `<div class="stack" data-testid="supervision-summary"><p-text size="sm">${escape(result.methodology)}</p-text><p-text size="sm" color="contrast-high">${escape(result.identity_scope)}</p-text>
      <p-text>${result.pending} revisão(ões) pendente(s) em ${result.total_cases} caso(s).</p-text>
      ${result.identity_counts ? `<p-text size="sm">Decisões com identidade autenticada: ${result.identity_counts.authenticated_decisions} · Decisões legadas ou autodeclaradas: ${result.identity_counts.legacy_or_declared_decisions}</p-text>` : ''}
      ${result.groups.map((group) => `<div class="decision-block"><p-heading tag="h3" size="md">${group.mode === 'real' ? 'IA real' : 'Síntese local'}</p-heading>
        <p-text>Concordância: ${ratio(group.agreement_rate)} · ${group.accept}/${group.reviewed} revisões</p-text>
        <p-text size="sm">Aceitações ${group.accept} · Ajustes ${group.adjust} · Rejeições ${group.reject}</p-text>
        ${group.disagreements.length ? `<p-text-list>${group.disagreements.map((item) => `<p-text-list-item>${escape(item.case_id)} · ${escape(item.actor)} · ${format(item.review)}: ${escape(item.reason)}</p-text-list-item>`).join('')}</p-text-list>` : '<p-text size="sm">Nenhuma discordância registrada neste grupo.</p-text>'}</div>`).join('')}
      ${result.alerts.length ? `<p-text-list>${result.alerts.map((item) => `<p-text-list-item>${escape(item.actor)} · ${escape(item.reason)} · Casos ${item.case_ids.map(escape).join(', ')}</p-text-list-item>`).join('')}</p-text-list>` : '<p-text size="sm">Nenhum sinal da heurística de revisão rápida. Isso não atesta a qualidade da supervisão.</p-text>'}</div>` : '<p-text size="sm">Calcule as taxas e consulte motivos de discordância com base nas decisões registradas.</p-text>'}`);
}

function detectionPanel() {
  const lastDetection = state.audit.findLast((event) => Array.isArray(event.details.case_ids));
  const noNewMatches = lastDetection && lastDetection.details.case_ids.length === 0;
  const rules = state.rules || [{ id: 'contact-code-match', name: 'Vínculo entre aprovador e fornecedor', description: 'Compara os códigos cadastrais do aprovador e do fornecedor.', version: '1', pending_count: state.dataset.contracts.filter((item) => !(state.detection?.processed_contract_ids || []).includes(item.id)).length }];
  return panel('Detecção de indícios', `<p-text>${cases().length} indício(s) registrado(s). Cada regra requer análise e revisão humana independentes.</p-text>
    ${noNewMatches ? '<p-inline-notification state="success" heading="Análise concluída sem novos indícios" description="A última execução não encontrou novos vínculos pela regra selecionada. Esse resultado não comprova ausência de outros riscos." dismiss-button="false"></p-inline-notification>' : ''}
    ${rules.map((rule) => `<section class="stack"><p-heading tag="h3" size="md">${escape(rule.name)}</p-heading><p-text size="sm">${escape(rule.description)}</p-text><p-text size="sm">Versão ${escape(rule.version)} · ${rule.pending_count} contrato(s) pendente(s)</p-text>
      <form class="form" data-endpoint="detect">${hidden('rule_id', rule.id)}<div class="actions"><p-button variant="${rule.id === 'contact-code-match' ? 'primary' : 'secondary'}" icon="none" data-testid="${rule.id === 'contact-code-match' ? 'detect' : 'detect-suppliers'}" type="submit"${!rule.pending_count ? ' disabled' : ''}>${rule.id === 'contact-code-match' ? 'Executar análise' : 'Analisar fornecedores relacionados'}</p-button></div></form></section>`).join('')}`);
}

function assistantPanel(current) {
  const queries = (state.assistant_queries || []).filter((query) => query.case_id === current.id);
  return panel('Assistente do caso', `<p-text>Consulte as fontes deste caso. As respostas não executam ações nem alteram decisões, riscos, maturidade ou planos. Arquivos anexados não são lidos.</p-text>
    <form class="form" data-endpoint="assistant/query" data-testid="assistant-form">
      ${hidden('case_id', current.id)}
      <p-textarea id="assistant-question" name="question" label="Pergunta sobre este caso" max-length="800" required compact></p-textarea>
      ${selectField('assistant-mode', 'mode', 'Modo da consulta', [['local', 'Consulta local por palavras (sem IA)'], ['real', 'IA real (requer configuração)']], 'local')}
      ${field('assistant-actor', 'actor', 'Responsável pela consulta')}
      <div class="actions"><p-button variant="secondary" icon="none" type="submit">Consultar fontes do caso</p-button></div>
    </form>
    ${queries.length ? [...queries].reverse().map((query) => `<section class="stack" data-testid="assistant-${escape(query.id)}">
      <p-heading tag="h3" size="md">${escape(query.question)}</p-heading>
      <p-text size="sm" color="contrast-high">${escape(query.id)} · ${escape(query.actor)} · ${query.mode === 'real' ? 'IA real' : 'Consulta local por palavras, sem IA'} · ${escape(query.model)}</p-text>
      <p-text size="sm">Fontes capturadas em ${escape(query.captured_at)}. A resposta preserva esse retrato e pode não refletir alterações posteriores.</p-text>
      ${query.abstained ? '<p-inline-notification state="info" heading="Sem resposta sustentada pelas fontes" description="Reformule a pergunta ou consulte os registros originais." dismiss-button="false"></p-inline-notification>' : `<p-text-list data-testid="assistant-claims">${query.claims.map((claim) => `<p-text-list-item><p-text>${escape(claim.text)}</p-text><p-text size="sm" color="contrast-high">Fontes: ${claim.source_ids.map(escape).join(', ')}</p-text></p-text-list-item>`).join('')}</p-text-list>`}
      <p-text>Limitações: ${escape(query.limitations)}</p-text><p-text>Próxima verificação humana: ${escape(query.suggestion)}</p-text>
      <p-text size="sm">${escape(query.scope)}${query.partial ? ' Contexto parcial: há trechos limitados ou planos fora desta consulta.' : ''}</p-text>
      <p-accordion><p-heading slot="summary" tag="h4" size="sm">Consultar fontes preservadas · ${escape(query.id)}</p-heading>
        <p-text-list>${query.sources.map((source) => `<p-text-list-item><div class="entry-content"><p-text weight="semibold">${escape(source.id)} · ${escape(source.source)}</p-text><p-text>${escape(source.detail)}</p-text>${source.truncated ? '<p-text size="sm">Trecho limitado a 700 caracteres.</p-text>' : ''}${source.revision ? `<p-text class="technical" size="xs">Revisão: ${escape(source.revision)}</p-text>` : ''}</div></p-text-list-item>`).join('')}</p-text-list>
      </p-accordion>
    </section>`).join('') : '<p-text size="sm">Nenhuma consulta registrada neste caso.</p-text>'}`);
}

function intelligence() {
  const title = heading('Central de inteligência', 'Revise o vínculo identificado, consulte as fontes e registre a decisão humana.');
  const current = state.case;
  if (!current) return `${title}<div class="grid">${detectionPanel()}<div class="stack">${datasetPanel()}${laboratoryPanel()}</div></div>`;
  const caseSummary = panel(`${escape(current.title || 'Possível conflito de interesses')} · ${escape(current.id)}`, '<p-text>O vínculo cadastral requer revisão humana. As evidências não demonstram, por si só, uma irregularidade.</p-text>', badge(current.status));
  return `${title}<div class="grid">
    <div class="stack">${caseSummary}${dossierPanel(current.dossier, Boolean(current.decision))}${decisionPanel(current)}${caseLinks()}${assistantPanel(current)}</div>
    <div class="stack">${memoryPanel()}${evidenceList(current)}${detectionPanel()}${datasetPanel()}${laboratoryPanel()}</div>
  </div>`;
}

function hidden(name, value) {
  return `<input type="hidden" name="${name}" value="${escape(value)}">`;
}

function selectField(id, name, label, options, value = '') {
  return `<p-select id="${id}" name="${name}" label="${label}" value="${escape(value)}" required>${options.map(([key, text]) => `<p-select-option value="${escape(key)}">${escape(text)}</p-select-option>`).join('')}</p-select>`;
}

function auditFields(prefix) {
  return `${field(`${prefix}-actor`, 'actor', 'Responsável pelo registro')}${paragraph(`${prefix}-reason`, 'reason', 'Justificativa do registro')}`;
}

function archiveForm(kind, item) {
  return `<p-accordion><p-heading slot="summary" tag="h4" size="sm">Arquivar ${escape(item.id)}</p-heading>
    <form class="form" data-endpoint="catalog/archive">${hidden('kind', kind)}${hidden('id', item.id)}${hidden('revision', item.revision)}
      <p-text size="sm">O histórico e os vínculos existentes são preservados. O registro deixa de ser oferecido em novos vínculos.</p-text>
      ${auditFields(`archive-${item.id}`)}<div class="actions"><p-button variant="secondary" icon="none" type="submit">Arquivar registro</p-button></div>
    </form></p-accordion>`;
}

function controlForm(item = {}) {
  const prefix = `control-${item.id || 'new'}`;
  return `<form class="form" data-endpoint="control/save" data-testid="${prefix}">
    ${item.id ? hidden('id', item.id) + hidden('revision', item.revision) : ''}
    ${field(`${prefix}-name`, 'name', 'Nome do controle', 'text', item.name)}
    ${paragraph(`${prefix}-description`, 'description', 'Descrição do controle', item.description)}
    ${auditFields(prefix)}<div class="actions"><p-button variant="secondary" icon="none" type="submit">${item.id ? 'Salvar controle' : 'Criar controle'}</p-button></div>
  </form>`;
}

function riskForm(item = {}) {
  const prefix = `risk-${item.id || 'new'}`;
  const controls = (state.controls || []).filter((control) => !control.archived || item.control_ids?.includes(control.id));
  return `<form class="form" data-endpoint="risk/save" data-testid="${prefix}">
    ${item.id ? hidden('id', item.id) + hidden('revision', item.revision) : ''}
    ${field(`${prefix}-name`, 'name', 'Nome do risco', 'text', item.name)}
    ${selectField(`${prefix}-level`, 'level', 'Exposição ao risco', ['Baixa', 'Moderada', 'Alta', 'Crítica'].map((value) => [value, value]), item.level || 'Moderada')}
    <p-text weight="semibold" size="sm">Controles vinculados</p-text>
    ${controls.map((control) => `<p-checkbox name="control_ids" value="${escape(control.id)}" label="${escape(control.name)}${control.archived ? ' (arquivado)' : ''}" autocomplete="off"${item.control_ids?.includes(control.id) ? ' checked' : ''}></p-checkbox>`).join('') || '<p-text size="sm">Cadastre controles para vinculá-los a este risco.</p-text>'}
    ${auditFields(prefix)}<div class="actions"><p-button variant="secondary" icon="none" type="submit">${item.id ? 'Salvar risco' : 'Criar risco'}</p-button></div>
  </form>`;
}

function catalogPanel() {
  const renderItem = (item, kind, form) => `<section class="entry-content" data-testid="catalog-${item.id}"><p-heading tag="h3" size="sm">${escape(item.id)} · ${escape(item.name)}${item.archived ? ' · Arquivado' : ''}</p-heading>
    ${item.archived ? '<p-text size="sm">Registro arquivado. Histórico preservado na trilha.</p-text>' : `<p-accordion><p-heading slot="summary" tag="h4" size="sm">Editar ${kind === 'risk' ? 'risco' : 'controle'}</p-heading>${form(item)}</p-accordion>${archiveForm(kind, item)}`}
  </section>`;
  return panel('Catálogo de riscos e controles', `<p-text size="sm" color="contrast-high">Registros compartilhados entre casos. Alterações exigem responsável e justificativa.</p-text>
    <p-accordion><p-heading slot="summary" tag="h3" size="sm">Novo controle</p-heading>${controlForm()}</p-accordion>
    ${(state.controls || []).map((item) => renderItem(item, 'control', controlForm)).join('')}
    <p-divider></p-divider><p-accordion><p-heading slot="summary" tag="h3" size="sm">Novo risco</p-heading>${riskForm()}</p-accordion>
    ${(state.risks || []).map((item) => renderItem(item, 'risk', riskForm)).join('')}`);
}

function dimensionForm(item = {}) {
  const prefix = `dimension-${item.id || 'new'}`;
  const questions = [...(item.questions || []), { id: '', text: '', weight: 1, max_score: 5 }];
  if (!item.id) questions.push({ id: '', text: '', weight: 1, max_score: 5 }, { id: '', text: '', weight: 1, max_score: 5 });
  return `<form class="form" data-endpoint="dimension/save" data-question-count="${questions.length}" data-testid="${prefix}">
    ${item.id ? hidden('id', item.id) + hidden('revision', item.revision) : ''}
    ${field(`${prefix}-name`, 'name', 'Nome da dimensão', 'text', item.name)}
    <p-text size="sm">Metodologia ilustrativa. Configure perguntas, pesos e pontuação máxima. Perguntas novas em branco são ignoradas; uma nova pergunta pode ser acrescentada a cada edição.</p-text>
    ${questions.map((question, index) => `<div class="decision-block">
      <p-heading tag="h4" size="sm">Pergunta ${index + 1}</p-heading>${hidden(`question_id_${index}`, question.id)}
      <p-input-text id="${prefix}-question-${index}" name="question_text_${index}" label="Pergunta" value="${escape(question.text)}"${index === 0 ? ' required' : ''}></p-input-text>
      <div class="form-grid"><p-input-number name="question_weight_${index}" label="Peso" value="${question.weight}" min="1" max="100" step="1"></p-input-number>
      <p-input-number name="question_max_${index}" label="Pontuação máxima" value="${question.max_score}" min="1" max="100" step="1"></p-input-number></div>
      ${question.id ? `<p-checkbox name="question_remove_${index}" value="true" label="Retirar esta pergunta" autocomplete="off"></p-checkbox>` : ''}
    </div>`).join('')}
    ${auditFields(prefix)}<div class="actions"><p-button variant="secondary" icon="none" type="submit">${item.id ? 'Salvar dimensão' : 'Criar dimensão'}</p-button></div>
  </form>`;
}

function assessmentForm(dimension) {
  const prefix = `assessment-${dimension.id}`;
  return `<form class="form" data-endpoint="maturity/assess" data-dimension-id="${escape(dimension.id)}" data-testid="${prefix}">
    ${hidden('dimension_id', dimension.id)}${hidden('dimension_revision', dimension.revision)}
    <p-text size="sm">Pontue cada pergunta com base nas evidências. O cálculo ponderado e as lacunas serão registrados após sua confirmação humana; a metodologia é ilustrativa.</p-text>
    ${dimension.questions.map((question, index) => `<div class="decision-block"><p-heading tag="h4" size="sm">${escape(question.text)}</p-heading>
      <p-text size="sm" color="contrast-high">Peso ${escape(question.weight)} · Máximo ${escape(question.max_score)}</p-text>
      <p-input-number name="answer_score_${index}" label="Pontuação" min="0" max="${question.max_score}" step="1" required></p-input-number>
      ${paragraph(`${prefix}-evidence-${index}`, `answer_evidence_${index}`, 'Evidência que sustenta a pontuação')}
    </div>`).join('')}
    ${auditFields(prefix)}
    <p-checkbox name="confirmed" value="true" label="Revisei as evidências e confirmo esta avaliação humana" required autocomplete="off"></p-checkbox>
    <div class="actions"><p-button variant="primary" icon="none" type="submit">Registrar avaliação de maturidade</p-button></div>
  </form>`;
}

function maturityCatalog() {
  const history = (state.assessments || []).map((item) => `<p-text-list-item><div class="entry-content">
    <p-text weight="semibold">${escape(item.id)} · ${escape(item.dimension_id)} · ${escape(item.score)}% · ${escape(item.level)}</p-text>
    <p-text size="sm">${escape(item.actor)} · ${escape(item.reason)}</p-text>
    <p-text-list>${item.answers.map((answer) => `<p-text-list-item>${escape(item.questions.find((question) => question.id === answer.question_id)?.text || answer.question_id)}: ${escape(answer.score)} · Lacuna ${escape(answer.gap)}. Evidência: ${escape(answer.evidence)}</p-text-list-item>`).join('')}</p-text-list>
  </div></p-text-list-item>`).join('');
  return panel('Avaliações de maturidade', `<p-tag variant="warning">Metodologia ilustrativa</p-tag>
    <p-accordion><p-heading slot="summary" tag="h3" size="sm">Nova dimensão</p-heading>${dimensionForm()}</p-accordion>
    ${(state.dimensions || []).map((dimension) => `<section class="entry-content" data-testid="catalog-${dimension.id}"><p-heading tag="h3" size="sm">${escape(dimension.id)} · ${escape(dimension.name)}${dimension.archived ? ' · Arquivada' : ''}</p-heading>
      ${dimension.archived ? '<p-text size="sm">Dimensão arquivada. Avaliações anteriores preservadas.</p-text>' : `<p-text weight="semibold">Nível atual: ${escape(dimension.level)}</p-text>
      <p-accordion><p-heading slot="summary" tag="h4" size="sm">Responder questionário</p-heading>${assessmentForm(dimension)}</p-accordion>
      <p-accordion><p-heading slot="summary" tag="h4" size="sm">Editar dimensão e perguntas</p-heading>${dimensionForm(dimension)}</p-accordion>${archiveForm('dimension', dimension)}`}
    </section>`).join('')}
    <p-divider></p-divider><p-heading tag="h3" size="md">Histórico das avaliações</p-heading>
    ${history ? `<p-text-list class="record-list" data-testid="assessments">${history}</p-text-list>` : '<p-text size="sm">Nenhuma avaliação registrada.</p-text>'}`);
}

function caseLinks() {
  const current = state.case;
  if (!current || current.decision) return '';
  return panel('Vínculos do caso', `<p-text size="sm">Escolha o risco e a dimensão antes da decisão humana. A fragilidade gerará propostas para esses registros compartilhados.</p-text>
    <form class="form" data-endpoint="case/link" data-testid="case-links">
      ${hidden('linkage_revision', current.linkage_revision)}
      ${selectField('case-risk', 'risk_id', 'Risco associado', (state.risks || []).filter((item) => !item.archived).map((item) => [item.id, item.name]), current.risk_id || 'RSK-001')}
      ${selectField('case-dimension', 'dimension_id', 'Dimensão associada', (state.dimensions || []).filter((item) => !item.archived).map((item) => [item.id, item.name]), current.dimension_id || 'DIM-001')}
      ${auditFields('case-link')}<div class="actions"><p-button variant="secondary" icon="none" type="submit">Salvar vínculos do caso</p-button></div>
    </form>`);
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
    <div class="grid">${panel('Impactos propostos', proposals)}<div class="stack">${risk}${maturity}</div></div><div class="grid">${catalogPanel()}${maturityCatalog()}</div><div class="grid">${connectionsPanel()}${scenarioPanel()}</div>`;
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

function attachmentUpload(action) {
  if (!state.case) return '';
  if (action && ['done', 'closure_requested'].includes(action.status)) return '<p-text size="sm" color="contrast-high">Os anexos da execução ficam preservados durante a revisão e após o encerramento.</p-text>';
  const caseId = action?.case_id || state.case.id;
  const key = `${caseId}-${action?.id || 'case'}`;
  const selected = selectedFiles.get(key);
  return `<form class="form" data-endpoint="evidence/upload" data-upload-key="${escape(key)}" data-testid="upload-${escape(key)}">
    ${hidden('case_id', caseId)}${action ? hidden('action_id', action.id) : ''}
    <p-text size="sm">TXT, PDF, PNG ou JPEG fictícios, até 1 MiB por arquivo e 20 MiB no ambiente. O conteúdo não é lido pelo modelo; o vínculo à evidência é registrado por uma pessoa.</p-text>
    <input type="file" hidden data-native-file-picker id="file-${escape(key)}" accept=".txt,.pdf,.png,.jpg,.jpeg" data-upload-key="${escape(key)}">
    <div class="actions"><p-button variant="secondary" icon="none" type="button" data-pick-file="file-${escape(key)}">Selecionar arquivo de evidência</p-button></div>
    <p-text size="sm" class="reading" data-selected-file="${escape(key)}" aria-live="polite">${selected ? `${escape(selected.name)} · ${selected.size} bytes` : 'Nenhum arquivo selecionado.'}</p-text>
    ${paragraph(`file-${key}-description`, 'description', 'Descrição e relação com o caso')}
    ${field(`file-${key}-actor`, 'actor', 'Responsável pelo anexo')}
    <p-checkbox name="synthetic" value="true" label="Confirmo que o arquivo contém somente dados fictícios" required autocomplete="off"></p-checkbox>
    <div class="actions"><p-button variant="secondary" icon="none" type="submit">Anexar evidência</p-button></div>
  </form>`;
}

function attachmentList(items) {
  return items.length ? `<p-text-list class="record-list">${items.map((item) => `<p-text-list-item><div class="entry-content" data-testid="attachment-${escape(item.id)}">
    <p-link variant="secondary" icon="none" href="/api/evidence/${encodeURIComponent(item.id)}" download>Baixar ${escape(item.name)}</p-link>
    <p-text size="sm">${escape(item.id)} · ${escape(item.size)} bytes · ${escape(item.actor)}${item.action_id ? ` · Plano ${escape(item.action_id)}` : ''}</p-text>
    <p-text>${escape(item.description)}</p-text><p-text class="technical" size="xs">SHA-256: ${escape(item.sha256)}</p-text>
  </div></p-text-list-item>`).join('')}</p-text-list>` : '<p-text size="sm" color="contrast-high">Nenhum arquivo de evidência anexado.</p-text>';
}

function caseAttachments() {
  if (!state.case) return '';
  return panel('Arquivos de evidência do caso', `${attachmentList((state.attachments || []).filter((item) => item.case_id === state.case.id))}
    <p-accordion><p-heading slot="summary" tag="h3" size="sm">Anexar arquivo ao caso</p-heading>${attachmentUpload()}</p-accordion>`);
}

function reportCase(item) {
  const decision = item.human_decision;
  return `<section class="entry-content"><p-heading tag="h4" size="md">Caso ${escape(item.case_id)}</p-heading>
    <p-text size="sm">${item.reviewed_dossier.mode === 'real' ? 'Afirmações de IA real revisadas' : 'Afirmações de síntese local revisadas'} · ${escape(item.reviewed_dossier.model)} · ${escape(item.reviewed_dossier.prompt_version)}</p-text>
    ${item.claim_status === 'excluded_by_human_rejection' ? '<p-text>As afirmações foram excluídas porque a sugestão foi rejeitada na revisão humana.</p-text>' : `<p-text-list data-testid="report-claims">${item.claims.map((claim) => `<p-text-list-item><p-text>${escape(claim.text)}</p-text><p-text size="sm" color="contrast-high">Fontes: ${claim.source_ids.map(escape).join(', ')}</p-text></p-text-list-item>`).join('')}</p-text-list><p-text class="reading">Limitações: ${escape(item.reviewed_dossier.limitations)}</p-text><p-text class="reading">Sugestão revisada: ${escape(item.reviewed_dossier.suggestion)}</p-text>`}
    <div class="decision-block"><p-text weight="semibold">Decisão humana: ${decisionOutcome(decision.outcome)} · ${escape(decision.actor)}</p-text><p-text>${format(decision.review)} · ${escape(decision.reason)}</p-text></div>
    <p-accordion><p-heading slot="summary" tag="h4" size="sm">Fontes preservadas · ${escape(item.case_id)}</p-heading><p-text-list>${item.sources.map((source) => `<p-text-list-item><p-text weight="semibold">${escape(source.id)} · ${escape(source.source)}</p-text><p-text>${escape(source.detail)}</p-text><p-text class="technical" size="sm">${escape(JSON.stringify(source.record, null, 2))}</p-text></p-text-list-item>`).join('')}</p-text-list></p-accordion>
  </section>`;
}

function reportsPanel() {
  const eligible = cases().filter((item) => item.decision && (item.decision.review === 'reject' || ['elo-dossier-v3', 'elo-dossier-v4'].includes(item.dossier?.prompt_version)));
  const create = eligible.length ? `<form class="form" data-endpoint="report/create" data-testid="report-create">
    ${field('report-title', 'title', 'Título do relatório')}
    <p-text weight="semibold" size="sm">Casos revisados a incluir (até 20)</p-text>
    ${eligible.map((item) => `<p-checkbox name="case_ids" value="${escape(item.id)}" label="${escape(item.id)} · ${decisionOutcome(item.decision.outcome)}" autocomplete="off"></p-checkbox>`).join('')}
    ${field('report-actor', 'actor', 'Responsável pela compilação')}
    <div class="actions"><p-button variant="secondary" icon="none" type="submit">Criar rascunho de relatório</p-button></div>
  </form>` : '<p-text size="sm">Revise um dossiê com afirmações e fontes e registre uma decisão humana para compilar o relatório. Casos com sugestão rejeitada podem ser incluídos com a decisão e as fontes, sem reutilizar suas afirmações.</p-text>';
  const reports = (state.reports || []).map((report) => `<section class="panel" data-testid="report-${escape(report.id)}"><div class="entry-header"><p-heading tag="h3" size="md">${escape(report.title)} · ${escape(report.id)}</p-heading>${badge(report.status)}</div>
    <p-text size="sm">${escape(report.scope)}</p-text><p-text size="sm">${escape(report.generation)}</p-text>
    <p-text size="sm" color="contrast-high">Compilado por ${escape(report.creator)} · ${escape(new Date(report.created_at).toLocaleString('pt-BR'))}</p-text>
    ${report.cases.map(reportCase).join('')}
    ${report.review ? `<div class="decision-block"><p-text weight="semibold">Revisão do relatório: ${format(report.review.outcome)} · ${escape(report.review.actor)}</p-text><p-text>${escape(report.review.reason)}</p-text></div>` : `<form class="form" data-endpoint="report/review" data-testid="review-${escape(report.id)}">
      ${hidden('id', report.id)}${hidden('report_revision', report.revision)}
      <p-text size="sm">Revise as afirmações, as fontes, as limitações e as decisões antes de aprovar. No modo autenticado, o revisor deve ser diferente de quem compilou.</p-text>
      ${selectField(`report-${report.id}-outcome`, 'outcome', 'Decisão sobre o relatório', [['approved', 'Aprovar relatório'], ['rejected', 'Recusar relatório']])}
      ${field(`report-${report.id}-reviewer`, 'actor', 'Revisor do relatório')}${paragraph(`report-${report.id}-reason`, 'reason', 'Justificativa da revisão do relatório')}
      <div class="actions"><p-button variant="primary" icon="none" type="submit">Registrar revisão do relatório</p-button></div>
    </form>`}</section>`).join('');
  return panel('Relatórios gerenciais', `<p-text size="sm">Compilação rastreável de afirmações já revisadas e decisões humanas. Não há nova chamada ao modelo. A aprovação do relatório é uma decisão separada.</p-text>
    <p-accordion><p-heading slot="summary" tag="h3" size="sm">Novo relatório gerencial</p-heading>${create}</p-accordion>${reports}`);
}

function encodeFile(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error('Não foi possível ler o arquivo selecionado.'));
    reader.onload = () => resolve(String(reader.result).split(',')[1]);
    reader.readAsDataURL(file);
  });
}

function actionCard(item) {
  const prefix = `action-${escape(item.id)}`;
  const identity = hidden('id', item.id) + hidden('case_id', item.case_id) + hidden('action_revision', item.revision);
  const update = ['done', 'closure_requested'].includes(item.status) ? '' : `<p-accordion><p-heading slot="summary" tag="h3" size="sm">Atualizar andamento</p-heading><form class="form" data-endpoint="action/update">
    ${identity}<div class="form-grid">
      ${selectField(`${prefix}-status`, 'status', 'Situação', ['open', 'in_progress', 'closure_requested'].map((status) => [status, labels[status]]), item.status)}
      ${field(`${prefix}-actor`, 'actor', 'Quem está registrando')}
    </div>${paragraph(`${prefix}-evidence`, 'evidence', 'Evidência de execução', item.evidence, false)}
    <p-text size="sm">Solicite o encerramento com evidência. A conclusão depende de revisão por outra pessoa.</p-text>
    <div class="actions"><p-button variant="secondary" icon="none" type="submit">Salvar andamento</p-button></div>
  </form></p-accordion>`;
  const edit = ['done', 'closure_requested'].includes(item.status) ? '' : `<p-accordion><p-heading slot="summary" tag="h3" size="sm">Editar responsável e prazo</p-heading>
    <form class="form" data-endpoint="action/edit">${identity}
      ${field(`${prefix}-edit-title`, 'title', 'Recomendação', 'text', item.title)}
      <div class="form-grid">${field(`${prefix}-edit-owner`, 'owner', 'Pessoa responsável', 'text', item.owner)}${field(`${prefix}-edit-due`, 'due', 'Prazo', 'date', item.due)}</div>
      ${auditFields(`${prefix}-edit`)}<div class="actions"><p-button variant="secondary" icon="none" type="submit">Salvar responsável e prazo</p-button></div>
    </form></p-accordion>`;
  const close = item.status !== 'closure_requested' ? '' : `<form class="form" data-endpoint="action/close" data-testid="close-${escape(item.id)}">
    ${identity}<p-text weight="semibold">Revisão do encerramento</p-text>
    <p-text size="sm">Solicitado por ${escape(item.closure_request?.actor)}. O revisor deve ser outra pessoa. ${session?.authenticated ? 'Identidades vinculadas às contas locais autenticadas.' : 'Identidades autodeclaradas nesta demonstração local.'}</p-text>
    ${selectField(`${prefix}-close-outcome`, 'outcome', 'Decisão de encerramento', [['approved', 'Aprovar encerramento'], ['rejected', 'Devolver para execução']])}
    ${field(`${prefix}-close-actor`, 'actor', 'Revisor do encerramento')}${paragraph(`${prefix}-close-reason`, 'reason', 'Justificativa da revisão')}
    <div class="actions"><p-button variant="primary" icon="none" type="submit">Registrar revisão de encerramento</p-button></div>
  </form>`;
  return `<p-text-list-item data-testid="action-item"><div class="entry-content">
    <div class="entry-header"><p-text weight="semibold">${escape(item.title)}</p-text>${badge(item.status)}</div>
    <p-text size="sm" color="contrast-high">Caso ${escape(item.case_id)} · ${escape(item.owner)} · Prazo ${escape(item.due)}</p-text>
    ${item.evidence ? `<p-text class="reading">Evidência: ${escape(item.evidence)}</p-text>` : ''}
    ${item.closure_review ? `<p-text size="sm">Revisão: ${escape(item.closure_review.actor)} · ${format(item.closure_review.outcome)} · ${escape(item.closure_review.reason)}</p-text>` : ''}
    ${attachmentList((state.attachments || []).filter((attachment) => attachment.action_id === item.id))}
    ${!['done', 'closure_requested'].includes(item.status) ? `<p-accordion><p-heading slot="summary" tag="h3" size="sm">Anexar evidência de execução</p-heading>${attachmentUpload(item)}</p-accordion>` : ''}
    ${update}${edit}${close}
  </div></p-text-list-item>`;
}

function auditEvent(event) {
  const time = new Date(event.at);
  const timestamp = Number.isFinite(time.valueOf()) ? time.toLocaleString('pt-BR') : event.at;
  return `<p-text-list-item data-testid="audit-event"><div class="entry-content">
    <p-text weight="semibold">${escape(event.seq)} · ${format(event.action)}</p-text>
    <p-text color="contrast-high" size="sm">${escape(event.actor)} · ${escape(timestamp)}</p-text>
    <p-text color="contrast-high" size="sm">${event.authentication?.mode === 'local-auth' ? 'Identidade local autenticada' : 'Registro local sem identidade autenticada'}</p-text>
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
    <div class="grid"><div class="stack">${panel('Plano de ação', `${actions}${actionForm()}`)}${panel('Supervisão humana', supervision(state.case))}${supervisionPanel()}${caseAttachments()}${reportsPanel()}</div>${panel('Trilha de auditoria', '<div class="actions"><p-link variant="secondary" icon="none" href="/api/audit/export" download="elo-auditoria.json">Exportar pacote de auditoria</p-link></div><p-text size="sm" color="contrast-high">Pacote JSON dos registros sintéticos locais, com trilha e hashes SHA-256 para verificação independente de integridade. Não equivale a uma assinatura digital.</p-text>' + eventList, status)}</div>`;
}

function render() {
  if (session?.auth_required && !session.authenticated) {
    document.title = 'Entrar | Elo';
    view.innerHTML = loginScreen();
    view.setAttribute('aria-busy', String(sending));
    return;
  }
  const current = location.hash.slice(1);
  const route = Object.hasOwn(views, current) ? current : 'visao';
  const pages = { visao: overview, inteligencia: intelligence, impactos: impacts, governanca: governance };
  document.title = `${views[route]} | Elo`;
  document.querySelector('p-tabs-bar').setAttribute('active-tab-index', Object.keys(views).indexOf(route));
  if (state) {
    view.innerHTML = `<div class="page">${sessionBanner()}${pages[route]()}</div>`;
    view.querySelectorAll('form[data-endpoint]').forEach((form) => {
      const reason = permissionReason(form.getAttribute('data-endpoint'), form);
      if (reason) form.outerHTML = `<p-text size="sm" color="contrast-high" data-testid="permission-notice">${escape(reason)}</p-text>`;
    });
  }
  view.setAttribute('aria-busy', String(sending));
}

async function read(url, payload) {
  const options = payload ? {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
  } : {};
  const response = await fetch(url, options);
  const result = await response.json();
  if (!response.ok) {
    const error = new Error(result.error || 'Não foi possível concluir a operação.');
    error.status = response.status;
    throw error;
  }
  return result;
}

function announce(message, error = false) {
  notice.hidden = !message;
  notice.innerHTML = message ? `<p-inline-notification state="${error ? 'error' : (sending ? 'info' : 'success')}" heading="${escape(message)}" dismiss-button="false"></p-inline-notification>` : '';
}

view.addEventListener('click', (event) => {
  const button = event.target.closest('[data-pick-file]');
  if (button && !sending) document.getElementById(button.getAttribute('data-pick-file'))?.click();
});

view.addEventListener('change', (event) => {
  const picker = event.target;
  if (!picker.matches('input[data-native-file-picker]')) return;
  const key = picker.getAttribute('data-upload-key');
  const file = picker.files?.[0];
  selectedFiles.delete(key);
  const label = [...view.querySelectorAll('[data-selected-file]')].find((element) => element.getAttribute('data-selected-file') === key);
  if (label) label.textContent = 'Nenhum arquivo selecionado.';
  if (!file) return;
  if (file.size > 1048576) { announce('O arquivo excede o limite de 1 MiB.', true); return; }
  if (!/\.(txt|pdf|png|jpe?g)$/i.test(file.name)) { announce('Selecione um arquivo TXT, PDF, PNG ou JPEG.', true); return; }
  selectedFiles.set(key, file);
  if (label) label.textContent = `${file.name} · ${file.size} bytes`;
  announce('Arquivo selecionado. Confirme os dados fictícios e registre a descrição antes de anexar.');
});

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
    const formData = new FormData(form);
    const payload = Object.fromEntries(formData);
    if (endpoint === 'scenario/create') {
      payload.likelihood = Number(payload.likelihood);
      payload.impact = Number(payload.impact);
      payload.risk_revision = state.risks.find((item) => item.id === payload.risk_id)?.revision;
    }
    if (endpoint === 'report/create') payload.case_ids = formData.getAll('case_ids');
    if (endpoint === 'evidence/upload') {
      const file = selectedFiles.get(form.getAttribute('data-upload-key'));
      if (!file) throw new Error('Selecione um arquivo de evidência antes de anexar.');
      if (file.size > 1048576) throw new Error('O arquivo excede o limite de 1 MiB.');
      payload.name = file.name;
      const extension = file.name.split('.').at(-1).toLowerCase();
      payload.media_type = file.type || ({txt:'text/plain',pdf:'application/pdf',png:'image/png',jpg:'image/jpeg',jpeg:'image/jpeg'}[extension] || 'application/octet-stream');
      payload.content_base64 = await encodeFile(file);
      payload.synthetic = payload.synthetic === 'true';
    }
    if (endpoint === 'risk/save') payload.control_ids = formData.getAll('control_ids');
    if (endpoint === 'dimension/save') {
      payload.questions = [];
      for (let index = 0; index < Number(form.getAttribute('data-question-count')); index++) {
        const text = payload[`question_text_${index}`]?.trim();
        if (text && !payload[`question_remove_${index}`]) payload.questions.push({
          id: payload[`question_id_${index}`] || `Q-${Date.now().toString(36)}-${index}`, text,
          weight: Number(payload[`question_weight_${index}`]), max_score: Number(payload[`question_max_${index}`]),
        });
      }
      Object.keys(payload).filter((key) => key.startsWith('question_')).forEach((key) => delete payload[key]);
    }
    if (endpoint === 'maturity/assess') {
      const dimension = state.dimensions.find((item) => item.id === payload.dimension_id);
      payload.answers = dimension.questions.map((question, index) => ({ question_id: question.id, score: Number(payload[`answer_score_${index}`]), evidence: payload[`answer_evidence_${index}`] }));
      payload.confirmed = payload.confirmed === 'true';
      Object.keys(payload).filter((key) => key.startsWith('answer_')).forEach((key) => delete payload[key]);
    }
    if (endpoint === 'login') {
      session = await read('/api/login', payload);
      await loadWorkspace();
    } else if (endpoint === 'logout') {
      session = await read('/api/logout', {});
      state = undefined;
      people = [];
      selectedFiles.clear();
      insights = undefined;
      insightsError = '';
      supervisionResult = undefined;
      laboratoryResult = undefined;
    } else if (endpoint === 'insights/read') {
      await refreshInsights();
    } else if (endpoint === 'laboratory/run' || endpoint === 'supervision/read') {
      if (endpoint === 'laboratory/run') laboratoryResult = await read('/api/laboratory');
      else supervisionResult = await read('/api/supervision');
    } else if (endpoint === 'select-case') {
      state = await read(`/api/state?case_id=${encodeURIComponent(payload.case_id)}`);
    } else {
      if (endpoint === 'import') {
        try { payload.dataset = JSON.parse(payload.dataset); }
        catch { throw new Error('A base deve conter um JSON válido. Revise o conteúdo antes de importar.'); }
        payload.synthetic = payload.synthetic === 'true';
      } else if (state.case && !payload.case_id) payload.case_id = state.case.id;
      state = await read(`/api/${endpoint}`, payload);
      if (endpoint === 'evidence/upload') selectedFiles.delete(form.getAttribute('data-upload-key'));
      supervisionResult = undefined;
    }
    if (state && !['login', 'laboratory/run', 'supervision/read', 'insights/read'].includes(endpoint)) await refreshInsights();
    if (state) selectedCaseId = state.case?.id || null;
    const url = new URL(location.href);
    if (selectedCaseId) url.searchParams.set('case_id', selectedCaseId);
    else url.searchParams.delete('case_id');
    history.replaceState(null, '', url);
    sending = false;
    announce(endpoint === 'login' ? 'Sessão iniciada.' : endpoint === 'logout' ? 'Sessão encerrada.' : endpoint === 'select-case' ? 'Caso selecionado.' : ['laboratory/run', 'supervision/read', 'insights/read'].includes(endpoint) ? 'Consulta concluída.' : 'Registro atualizado.');
    render();
    view.querySelector('p-heading[tag=h1]')?.focus({ preventScroll: true });
  } catch (error) {
    if (form.getAttribute('data-endpoint') !== 'login' || session?.authenticated) expiredSession(error);
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
    session = await read('/api/session');
    if (!session.auth_required || session.authenticated) await loadWorkspace();
    render();
  } catch (error) {
    if (!expiredSession(error)) view.innerHTML = '<p-text color="contrast-high">Recarregue a página para tentar se conectar novamente.</p-text>';
    announce(error.message, true);
    view.setAttribute('aria-busy', 'false');
  }
}

initialize();
