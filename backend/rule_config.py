"""Versioned, bounded parameters for the two deterministic synthetic rules."""
from copy import deepcopy
import hashlib
from domain import RULES, WorkflowError, required, require, serialize


def stamp(config):
    config['revision'] = hashlib.sha256(serialize({k: v for k, v in config.items() if k != 'revision'}).encode()).hexdigest()
    return config


def defaults(rule_id):
    require(rule_id in RULES, 'Regra desconhecida.')
    return stamp({'rule_id': rule_id, 'version': 1, 'enabled': True, 'min_code_length': 1,
                  'excluded_contact_codes': [], 'contract_title_contains': ''})


def get_config(state, rule_id):
    require(rule_id in RULES, 'Regra desconhecida.')
    return deepcopy(state.get('rule_configs', {}).get(rule_id, defaults(rule_id)))


def save(state, data):
    actor, reason = required(data, 'actor', 80), required(data, 'reason')
    rule_id = required(data, 'rule_id', 64)
    current = get_config(state, rule_id)
    require(required(data, 'revision', 64) == current['revision'], 'A configuração mudou. Atualize e revise a regra.')
    enabled, length = data.get('enabled'), data.get('min_code_length')
    codes, title = data.get('excluded_contact_codes'), data.get('contract_title_contains')
    if not isinstance(enabled, bool) or type(length) is not int or not 1 <= length <= 160:
        raise WorkflowError('Informe ativação e comprimento mínimo entre 1 e 160.')
    if (not isinstance(codes, list) or len(codes) > 30 or any(not isinstance(c, str) or not c.strip() or len(c.strip()) > 160 for c in codes)
            or len(set(c.strip() for c in codes)) != len(codes)):
        raise WorkflowError('Informe até 30 códigos não vazios e distintos para excluir.')
    if not isinstance(title, str) or len(title.strip()) > 160:
        raise WorkflowError('Filtro do título deve ter até 160 caracteres.')
    config = stamp({'rule_id': rule_id, 'version': current['version'] + 1, 'enabled': enabled,
                    'min_code_length': length, 'excluded_contact_codes': [c.strip() for c in codes],
                    'contract_title_contains': title.strip()})
    state.setdefault('rule_configs', {})[rule_id] = config
    detection = state.get('detection')
    if detection:
        detection.get('processed_by_rule', {}).pop(rule_id, None)
        if rule_id == 'contact-code-match':
            detection['processed_contract_ids'] = []
    return 'Parâmetros da regra atualizados', actor, {'rule_id': rule_id, 'previous': current, 'configuration': deepcopy(config), 'reason': reason}


def snapshot(state, rule_id):
    return {**deepcopy(RULES[rule_id]), 'configuration': get_config(state, rule_id)}


def match(dataset, rule_id, config):
    from domain import match_cases, match_supplier_cases
    require(config['rule_id'] == rule_id and rule_id in RULES, 'Configuração incompatível com a regra.')
    if not config['enabled']:
        return []
    matcher = match_cases if rule_id == 'contact-code-match' else match_supplier_cases
    title = config['contract_title_contains'].casefold()
    candidates = {**dataset, 'contracts': [row for row in dataset['contracts'] if title in row['title'].casefold()]}
    output = []
    for case in matcher(candidates):
        code = case['records']['supplier']['contact_code']
        if len(code) < config['min_code_length'] or code in config['excluded_contact_codes']:
            continue
        case['rule']['configuration'] = deepcopy(config)
        output.append(case)
    return output
