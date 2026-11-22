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
  open: 'Aberto', in_progress: 'Em andamento', done: 'Concluído', closure_requested: 'Aguardando aprovação de encerramento', risk: 'Risco', maturity: 'Maturidade',
  low: 'Baixa', medium: 'Média', high: 'Alta', critical: 'Crítica',
  alert_detected: 'Indício detectado', dossier_generated: 'Dossiê gerado', decision_recorded: 'Decisão humana registrada',
  impact_decided: 'Impacto avaliado', action_created: 'Plano de ação criado', action_updated: 'Plano de ação atualizado',
};

const view = document.querySelector('#view');
const notice = document.querySelector('#notice');
let state;
let sending = false;
let laboratoryResult;
let supervisionResult;
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

function field(id, name, label, type = 'text', value = '') {
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
      ${result.groups.map((group) => `<div class="decision-block"><p-heading tag="h3" size="md">${group.mode === 'real' ? 'IA real' : 'Síntese local'}</p-heading>
        <p-text>Concordância: ${ratio(group.agreement_rate)} · ${group.accept}/${group.reviewed} revisões</p-text>
        <p-text size="sm">Aceitações ${group.accept} · Ajustes ${group.adjust} · Rejeições ${group.reject}</p-text>
        ${group.disagreements.length ? `<p-text-list>${group.disagreements.map((item) => `<p-text-list-item>${escape(item.case_id)} · ${escape(item.actor)} · ${format(item.review)}: ${escape(item.reason)}</p-text-list-item>`).join('')}</p-text-list>` : '<p-text size="sm">Nenhuma discordância registrada neste grupo.</p-text>'}</div>`).join('')}
      ${result.alerts.length ? `<p-text-list>${result.alerts.map((item) => `<p-text-list-item>${escape(item.actor)} · ${escape(item.reason)} · Casos ${item.case_ids.map(escape).join(', ')}</p-text-list-item>`).join('')}</p-text-list>` : '<p-text size="sm">Nenhum sinal da heurística de revisão rápida. Isso não atesta a qualidade da supervisão.</p-text>'}</div>` : '<p-text size="sm">Calcule as taxas e consulte motivos de discordância com base nas decisões registradas.</p-text>'}`);
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
  if (!current) return `${title}<div class="grid">${detectionPanel()}<div class="stack">${datasetPanel()}${laboratoryPanel()}</div></div>`;
  const caseSummary = panel(`Possível conflito de interesses · ${escape(current.id)}`, '<p-text>O vínculo cadastral requer revisão humana. As evidências não demonstram, por si só, uma irregularidade.</p-text>', badge(current.status));
  return `${title}<div class="grid">
    <div class="stack">${caseSummary}${dossierPanel(current.dossier, Boolean(current.decision))}${decisionPanel(current)}${caseLinks()}</div>
    <div class="stack">${evidenceList(current)}${detectionPanel()}${datasetPanel()}${laboratoryPanel()}</div>
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
    <div class="grid">${panel('Impactos propostos', proposals)}<div class="stack">${risk}${maturity}</div></div><div class="grid">${catalogPanel()}${maturityCatalog()}</div>`;
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
    <p-text size="sm">Solicitado por ${escape(item.closure_request?.actor)}. O revisor deve ser outra pessoa. Identidades autodeclaradas nesta demonstração local.</p-text>
    ${selectField(`${prefix}-close-outcome`, 'outcome', 'Decisão de encerramento', [['approved', 'Aprovar encerramento'], ['rejected', 'Devolver para execução']])}
    ${field(`${prefix}-close-actor`, 'actor', 'Revisor do encerramento')}${paragraph(`${prefix}-close-reason`, 'reason', 'Justificativa da revisão')}
    <div class="actions"><p-button variant="primary" icon="none" type="submit">Registrar revisão de encerramento</p-button></div>
  </form>`;
  return `<p-text-list-item data-testid="action-item"><div class="entry-content">
    <div class="entry-header"><p-text weight="semibold">${escape(item.title)}</p-text>${badge(item.status)}</div>
    <p-text size="sm" color="contrast-high">Caso ${escape(item.case_id)} · ${escape(item.owner)} · Prazo ${escape(item.due)}</p-text>
    ${item.evidence ? `<p-text class="reading">Evidência: ${escape(item.evidence)}</p-text>` : ''}
    ${item.closure_review ? `<p-text size="sm">Revisão: ${escape(item.closure_review.actor)} · ${format(item.closure_review.outcome)} · ${escape(item.closure_review.reason)}</p-text>` : ''}
    ${update}${edit}${close}
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
    <div class="grid"><div class="stack">${panel('Plano de ação', `${actions}${actionForm()}`)}${panel('Supervisão humana', supervision(state.case))}${supervisionPanel()}</div>${panel('Trilha de auditoria', '<div class="actions"><p-link variant="secondary" icon="none" href="/api/audit/export" download="elo-auditoria.json">Exportar pacote de auditoria</p-link></div><p-text size="sm" color="contrast-high">Pacote JSON dos registros sintéticos locais, com trilha e hashes SHA-256 para verificação independente de integridade. Não equivale a uma assinatura digital.</p-text>' + eventList, status)}</div>`;
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
    const formData = new FormData(form);
    const payload = Object.fromEntries(formData);
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
    if (endpoint === 'laboratory/run' || endpoint === 'supervision/read') {
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
      supervisionResult = undefined;
    }
    selectedCaseId = state.case?.id || null;
    const url = new URL(location.href);
    if (selectedCaseId) url.searchParams.set('case_id', selectedCaseId);
    else url.searchParams.delete('case_id');
    history.replaceState(null, '', url);
    sending = false;
    announce(endpoint === 'select-case' ? 'Caso selecionado.' : endpoint === 'laboratory/run' || endpoint === 'supervision/read' ? 'Consulta concluída.' : 'Registro atualizado.');
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
