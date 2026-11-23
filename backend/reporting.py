"""Management report snapshots reusing reviewed claims; no new model invocation."""

import hashlib
import re
from copy import deepcopy
from datetime import datetime, timezone

from domain import WorkflowError, choice, required, require, serialize

COMMANDS = {'report/create', 'report/review'}
SOURCE_FIELDS = {
    'EMP-': ('employees', ('id', 'name', 'role', 'contact_code')),
    'FOR-': ('suppliers', ('id', 'name', 'contact_code')),
    'CTR-': ('contracts', ('id', 'title', 'supplier_id', 'approver_id')),
}


def normalize(state):
    state.setdefault('reports', [])
    return state


def revision(report):
    return hashlib.sha256(serialize({key: value for key, value in report.items() if key != 'revision'}).encode('utf-8')).hexdigest()


def source_snapshots(state, case):
    evidence = case.get('evidence')
    require(isinstance(evidence, list) and 1 <= len(evidence) <= 20,
            'O caso não contém fontes válidas para o relatório.')
    sources, known = [], set()
    case_records = case.get('records') or {}
    for source in evidence:
        identifier = required(source, 'id', 64)
        require(identifier not in known, 'O caso contém fontes duplicadas.')
        known.add(identifier)
        spec = next((value for prefix, value in SOURCE_FIELDS.items() if identifier.startswith(prefix)), None)
        require(spec is not None, 'A fonte não possui registro de origem compatível.')
        table, fields = spec
        record = next((row for row in case_records.values() if isinstance(row, dict) and row.get('id') == identifier), None)
        if record is None:
            record = next((row for row in state.get('dataset', {}).get(table, []) if row.get('id') == identifier), None)
        require(record is not None and all(isinstance(record.get(key), str) and len(record[key]) <= 500 for key in fields),
                'Uma fonte não tem registro de origem disponível. Use um caso com fontes preservadas.')
        sources.append({'id': identifier, 'source': required(source, 'source', 160),
                        'detail': required(source, 'detail', 1000),
                        'record': {key: record[key] for key in fields}})
    return sources


def reviewed_case(state, case):
    decision = case.get('decision')
    dossier = case.get('dossier')
    require(isinstance(decision, dict) and isinstance(dossier, dict),
            'Revise o dossiê e registre uma decisão humana em cada caso antes de criar o relatório.')
    review = choice(decision, 'review', ('accept', 'adjust', 'reject'))
    outcome = choice(decision, 'outcome', ('discard', 'monitor', 'qualify'))
    dossier_revision = required(dossier, 'revision', 64)
    require(decision.get('dossier_revision') == dossier_revision,
            'A decisão não corresponde à revisão do dossiê preservado.')
    sources = source_snapshots(state, case)
    known = {source['id'] for source in sources}
    copied_claims = []
    if review != 'reject':
        claims = dossier.get('claims')
        require(dossier.get('prompt_version') in {'elo-dossier-v3', 'elo-dossier-v4'} and isinstance(claims, list) and 1 <= len(claims) <= 6,
                'O caso usa dossiê legado sem afirmações estruturadas. Selecione um caso com dossiê estruturado v3/v4 revisado para reutilizar as afirmações.')
        for claim in claims:
            text = required(claim, 'text', 2400)
            ids = claim.get('source_ids')
            require(isinstance(ids, list) and 1 <= len(ids) <= 20 and all(isinstance(item, str) and item in known for item in ids),
                    'A afirmação possui fonte ausente ou desconhecida; não é possível incluí-la no relatório.')
            require(set(re.findall(r'\b(?:CTR|FOR|EMP)-[A-Za-z0-9_-]+', text)).issubset(known),
                    'A afirmação menciona registro desconhecido.')
            copied_claims.append({'case_id': case['id'], 'text': text, 'source_ids': list(dict.fromkeys(ids))})
        require(sum(len(claim['text']) for claim in copied_claims) <= 2400,
                'As afirmações do caso excedem o limite do relatório.')
    mode = choice(dossier, 'mode', ('real', 'local'))
    provenance = {'revision': dossier_revision, 'mode': mode,
                  'model': required(dossier, 'model', 240),
                  'prompt_version': required(dossier, 'prompt_version', 80)}
    if review != 'reject':
        provenance['limitations'] = required(dossier, 'limitations', 2400)
        provenance['suggestion'] = required(dossier, 'suggestion', 2400)
    return {
        'case_id': case['id'],
        'human_decision': {'origin': 'human', 'review': review, 'outcome': outcome,
                           'actor': required(decision, 'actor', 80), 'reason': required(decision, 'reason', 500),
                           'dossier_revision': dossier_revision},
        'reviewed_dossier': provenance,
        'claims': copied_claims, 'sources': sources,
        'claim_status': 'excluded_by_human_rejection' if review == 'reject' else 'reused_from_reviewed_dossier',
    }


def transition(state, command, data):
    require(command in COMMANDS, 'Ação de relatório desconhecida.')
    normalize(state)
    actor = required(data, 'actor', 80)
    if command == 'report/create':
        require(len(state['reports']) < 200, 'Limite local de 200 relatórios atingido.')
        title = required(data, 'title', 160)
        identifiers = data.get('case_ids')
        if (not isinstance(identifiers, list) or not 1 <= len(identifiers) <= 20
                or any(not isinstance(identifier, str) or not 1 <= len(identifier) <= 64 for identifier in identifiers)
                or len(set(identifiers)) != len(identifiers)):
            raise WorkflowError('Selecione de 1 a 20 casos distintos para o relatório.')
        available = state.get('cases', [state['case']] if state.get('case') else [])
        cases = {case['id']: case for case in available}
        require(all(identifier in cases for identifier in identifiers), 'Um dos casos selecionados não existe.')
        snapshots = [reviewed_case(state, cases[identifier]) for identifier in identifiers]
        report = {
            'id': f'RPT-{len(state["reports"]) + 1:03}', 'title': title, 'status': 'draft',
            'creator': actor, 'created_at': datetime.now(timezone.utc).isoformat(timespec='milliseconds'),
            'scope': 'Relatório local com dados sintéticos. Não comprova irregularidade.',
            'generation': 'Compilação de decisões humanas e afirmações de dossiês já revisados; nenhuma nova chamada de IA.',
            'case_ids': list(identifiers), 'cases': snapshots,
        }
        report['revision'] = revision(report)
        state['reports'].append(report)
        return 'Rascunho de relatório criado', actor, {'report_id': report['id'], 'report_revision': report['revision'],
                                                     'case_ids': list(identifiers), 'title': title}
    identifier = required(data, 'id', 32)
    report = next((item for item in state['reports'] if item['id'] == identifier), None)
    require(report is not None, 'Relatório não encontrado.')
    require(report['status'] == 'draft', 'O relatório já foi revisado e não pode ser alterado. Crie outro rascunho.')
    require(required(data, 'report_revision', 64) == report['revision'],
            'O relatório mudou. Atualize a página e revise a versão atual.')
    outcome = choice(data, 'outcome', ('approved', 'rejected'))
    reason = required(data, 'reason', 500)
    reviewed_revision = report['revision']
    report['status'] = outcome
    report['review'] = {'actor': actor, 'reason': reason, 'outcome': outcome, 'reviewed_revision': reviewed_revision,
                        'at': datetime.now(timezone.utc).isoformat(timespec='milliseconds')}
    report['revision'] = revision(report)
    return 'Relatório revisado', actor, {'report_id': report['id'], 'report_revision': report['revision'],
                                       'reviewed_revision': reviewed_revision, 'outcome': outcome, 'reason': reason,
                                       'case_ids': deepcopy(report['case_ids'])}
