"""Human-owned catalogs, illustrative assessments and reviewed action closure."""
import hashlib
import math
import re
from copy import deepcopy
from datetime import date

from domain import WorkflowError, choice, require, required, serialize

KINDS = {'risk': ('risks', 'RSK'), 'control': ('controls', 'CTL'), 'dimension': ('dimensions', 'DIM')}
COMMANDS = {'risk/save', 'control/save', 'dimension/save', 'catalog/archive', 'maturity/assess', 'case/link'}
LEVELS = ('Baixa', 'Moderada', 'Alta', 'Crítica')


def revision(item):
    return hashlib.sha256(serialize({key: value for key, value in item.items() if key != 'revision'}).encode()).hexdigest()


def stamp(item):
    item['revision'] = revision(item)
    return item


def lookup(state, kind, identifier):
    require(isinstance(identifier, str), 'Identificador inválido.')
    table = KINDS[kind][0]
    item = next((row for row in state[table] if row['id'] == identifier), None)
    require(item is not None, 'Registro não encontrado.')
    return item


def cas(item, data, key='revision'):
    require(required(data, key, 64) == item['revision'], 'O registro mudou. Atualize a página e revise a versão atual.')


def normalize(state):
    if 'controls' not in state:
        state['controls'] = [{'id': f'CTL-{index:03}', 'name': name, 'description': 'Controle inicial da demonstração.', 'archived': False}
                             for index, name in enumerate(state['risk']['controls'], 1)]
    if 'risks' not in state:
        state['risks'] = [{'id': 'RSK-001', 'name': state['risk']['name'], 'level': state['risk']['level'],
                           'control_ids': [row['id'] for row in state['controls']], 'archived': False}]
    if 'dimensions' not in state:
        state['dimensions'] = [{'id': 'DIM-001', 'name': state['maturity']['name'], 'level': state['maturity']['level'],
            'methodology': 'Ilustrativa', 'archived': False, 'questions': [
                {'id': 'Q1', 'text': 'A diligência de terceiros é documentada e executada?', 'weight': 1, 'max_score': 4},
                {'id': 'Q2', 'text': 'Os vínculos relevantes são revisados com evidências?', 'weight': 1, 'max_score': 4}]}]
    state.setdefault('assessments', [])
    for case in state['cases']:
        case.setdefault('risk_id', 'RSK-001')
        case.setdefault('dimension_id', 'DIM-001')
        case['linkage_revision'] = revision({key: case.get(key) for key in ('risk_id', 'dimension_id', 'linkage')})
    for control in state['controls']:
        stamp(control)
    for risk in state['risks']:
        risk['controls'] = [row['name'] for row in state['controls'] if row['id'] in risk['control_ids']]
        risk['control_revisions'] = {row['id']: row['revision'] for row in state['controls'] if row['id'] in risk['control_ids']}
    for table in ('risks', 'dimensions', 'actions'):
        for item in state[table]:
            stamp(item)
    for case in state['cases']:
        linked = targets(state, case)
        for impact in case.get('impacts', []):
            if impact.get('status') == 'pending' and 'target_revision' not in impact:
                target = linked[impact['kind']]
                impact['target_id'] = target['id']
                impact['target_revision'] = target['revision']
    state['risk'] = state['risks'][0]
    state['maturity'] = state['dimensions'][0]
    return state


def targets(state, case):
    return {'risk': lookup(state, 'risk', case.get('risk_id', 'RSK-001')),
            'maturity': lookup(state, 'dimension', case.get('dimension_id', 'DIM-001'))}


def validate_questions(value):
    if not isinstance(value, list) or not 1 <= len(value) <= 50:
        raise WorkflowError('Informe entre 1 e 50 perguntas.')
    result, identifiers = [], set()
    for row in value:
        if not isinstance(row, dict):
            raise WorkflowError('Pergunta inválida.')
        identifier = required(row, 'id', 32)
        if not re.fullmatch(r'[A-Za-z0-9_-]+', identifier) or identifier in identifiers:
            raise WorkflowError('IDs das perguntas devem ser únicos e alfanuméricos.')
        identifiers.add(identifier)
        weight, maximum = row.get('weight'), row.get('max_score')
        for number in (weight, maximum):
            if isinstance(number, bool) or not isinstance(number, (int, float)) or not math.isfinite(number) or not 0 < number <= 100:
                raise WorkflowError('Pesos e pontuações máximas devem ser números positivos até 100.')
        result.append({'id': identifier, 'text': required(row, 'text', 500), 'weight': weight, 'max_score': maximum})
    return result


def transition(state, command, data):
    actor, reason = required(data, 'actor', 80), required(data, 'reason')
    if command.endswith('/save'):
        kind = command.split('/')[0]
        table, prefix = KINDS[kind]
        existing = lookup(state, kind, data['id']) if data.get('id') else None
        if existing:
            cas(existing, data)
            require(not existing['archived'], 'Registro arquivado não pode ser alterado.')
        else:
            require(len(state[table]) < 200, 'Limite local de 200 registros por catálogo atingido.')
        item = deepcopy(existing) if existing else {'id': f'{prefix}-{len(state[table]) + 1:03}', 'archived': False}
        item['name'] = required(data, 'name', 160)
        if kind == 'risk':
            item['level'] = choice(data, 'level', LEVELS)
            control_ids = data.get('control_ids')
            if not isinstance(control_ids, list) or len(control_ids) > 200 or any(not isinstance(i, str) for i in control_ids) or len(set(control_ids)) != len(control_ids):
                raise WorkflowError('Informe uma lista de controles únicos.')
            for identifier in control_ids:
                control = lookup(state, 'control', identifier)
                require(not control['archived'] or (existing is not None and identifier in existing['control_ids']),
                        'Controle arquivado não pode ser associado a um novo risco.')
            item['control_ids'] = control_ids
        elif kind == 'control':
            item['description'] = required(data, 'description')
        else:
            item.update(questions=validate_questions(data.get('questions')), methodology='Ilustrativa')
            if not existing:
                item['level'] = 'Não avaliada'
            elif item['questions'] != existing['questions']:
                item['level'] = 'Reavaliação necessária'
        if existing:
            existing.clear()
            existing.update(item)
        else:
            state[table].append(item)
        normalize(state)
        return 'Catálogo atualizado', actor, {'kind': kind, 'record': deepcopy(lookup(state, kind, item['id'])), 'reason': reason}
    if command == 'catalog/archive':
        kind = choice(data, 'kind', KINDS)
        item = lookup(state, kind, required(data, 'id', 32))
        cas(item, data)
        require(not item['archived'], 'Registro já arquivado.')
        item['archived'] = True
        stamp(item)
        return 'Registro arquivado', actor, {'kind': kind, 'id': item['id'], 'reason': reason}
    if command == 'case/link':
        from domain import selected_case
        case = selected_case(state, required(data, 'case_id', 64))
        require(case['decision'] is None, 'Os vínculos não podem mudar após a decisão humana.')
        require(required(data, 'linkage_revision', 64) == case['linkage_revision'], 'Os vínculos mudaram. Atualize a página e revise a versão atual.')
        risk = lookup(state, 'risk', required(data, 'risk_id', 32))
        dimension = lookup(state, 'dimension', required(data, 'dimension_id', 32))
        require(not risk['archived'] and not dimension['archived'], 'Escolha registros ativos.')
        case.update(risk_id=risk['id'], dimension_id=dimension['id'], linkage={'actor': actor, 'reason': reason})
        return 'Vínculos do caso revisados', actor, {'case_id': case['id'], 'risk_id': risk['id'], 'dimension_id': dimension['id'], 'reason': reason}
    dimension = lookup(state, 'dimension', required(data, 'dimension_id', 32))
    cas(dimension, data, 'dimension_revision')
    require(not dimension['archived'], 'Dimensão arquivada não pode ser avaliada.')
    if data.get('confirmed') is not True:
        raise WorkflowError('Confirme a avaliação humana pela metodologia ilustrativa.')
    answers = data.get('answers')
    questions = dimension['questions']
    if not isinstance(answers, list) or len(answers) != len(questions) or any(not isinstance(row, dict) for row in answers):
        raise WorkflowError('Responda todas as perguntas da dimensão.')
    mapped = {}
    for row in answers:
        identifier = required(row, 'question_id', 32)
        if identifier in mapped:
            raise WorkflowError('Pergunta respondida mais de uma vez.')
        mapped[identifier] = row
    if set(mapped) != {row['id'] for row in questions}:
        raise WorkflowError('As respostas não correspondem ao questionário atual.')
    checked, weighted = [], 0
    for question in questions:
        answer = mapped[question['id']]
        score = answer.get('score')
        if isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(score) or not 0 <= score <= question['max_score']:
            raise WorkflowError('Pontuação fora dos limites da pergunta.')
        weighted += score / question['max_score'] * question['weight']
        checked.append({'question_id': question['id'], 'score': score, 'evidence': required(answer, 'evidence'), 'gap': question['max_score'] - score})
    score = round(100 * weighted / sum(row['weight'] for row in questions), 2)
    level = 'Inicial' if score < 40 else 'Intermediária' if score < 80 else 'Avançada'
    assessment = {'id': f'AVA-{len(state["assessments"]) + 1:03}', 'dimension_id': dimension['id'], 'dimension_revision': dimension['revision'],
                  'actor': actor, 'reason': reason, 'methodology': 'Ilustrativa', 'questions': deepcopy(questions), 'answers': checked, 'score': score, 'level': level}
    state['assessments'].append(assessment)
    dimension['level'] = level
    dimension['latest_assessment_id'] = assessment['id']
    stamp(dimension)
    return 'Avaliação humana de maturidade registrada', actor, deepcopy(assessment)


def valid_due(data):
    due = required(data, 'due', 10)
    try:
        if date.fromisoformat(due).isoformat() != due:
            raise ValueError
    except ValueError as error:
        raise WorkflowError('Informe um prazo válido (AAAA-MM-DD).') from error
    return due


def action_transition(state, command, data, case):
    actor = required(data, 'actor', 80)
    item = next((row for row in state['actions'] if row['id'] == data.get('id') and row['case_id'] == case['id']), None)
    require(item is not None, 'Recomendação não encontrada.')
    cas(item, data, 'action_revision')
    require(item['status'] != 'done', 'Plano concluído não pode ser alterado.')
    if command == 'action/edit':
        require(item['status'] != 'closure_requested', 'Decida o encerramento pendente antes de editar o plano.')
        reason = required(data, 'reason')
        item.update(title=required(data, 'title', 160), owner=required(data, 'owner', 80), due=valid_due(data))
        stamp(item)
        return 'Plano de ação editado', actor, {**deepcopy(item), 'reason': reason}
    if command == 'action/close':
        require(item['status'] == 'closure_requested', 'Solicite o encerramento antes da revisão.')
        require(actor.casefold() != item['closure_request']['actor'].casefold(), 'A revisão exige uma pessoa diferente de quem solicitou o encerramento.')
        outcome = choice(data, 'outcome', ('approved', 'rejected'))
        reason = required(data, 'reason')
        item.update(status='done' if outcome == 'approved' else 'in_progress', closure_review={'actor': actor, 'reason': reason, 'outcome': outcome})
        stamp(item)
        return 'Encerramento revisado', actor, deepcopy(item)
    require(command == 'action/update', 'Ação desconhecida.')
    require(item['status'] != 'closure_requested', 'Decida o encerramento pendente antes de atualizar o plano.')
    status = choice(data, 'status', ('open', 'in_progress', 'closure_requested', 'done'))
    evidence = data.get('evidence', '')
    if not isinstance(evidence, str) or len(evidence.strip()) > 500:
        raise WorkflowError('Informe uma evidência com até 500 caracteres.')
    evidence = evidence.strip()
    if status in ('closure_requested', 'done'):
        if not evidence:
            raise WorkflowError('Registre uma evidência para solicitar o encerramento.')
        status = 'closure_requested'
        item['closure_request'] = {'actor': actor, 'evidence': evidence}
        item.pop('closure_review', None)
    item.update(status=status, evidence=evidence)
    stamp(item)
    return 'Encerramento solicitado' if status == 'closure_requested' else 'Recomendação atualizada', actor, deepcopy(item)
