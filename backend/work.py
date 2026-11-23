"""Human-managed second-line work, independent of detected cases."""
import hashlib
from copy import deepcopy
from datetime import date, datetime, timezone
from statistics import median
from zoneinfo import ZoneInfo

from domain import WorkflowError, choice, require, required, serialize
from operations import overview

COMMANDS = {'work/create', 'work/update', 'work/status'}
PRIORITIES = ('low', 'normal', 'high', 'urgent')
STATUSES = ('planned', 'in_progress', 'completed', 'cancelled')
MAX_ITEMS = 2000


def utc_now():
    return datetime.now(timezone.utc)


def normalize(state):
    state.setdefault('work_items', [])
    return state


def revision(item):
    return hashlib.sha256(serialize({key: value for key, value in item.items() if key != 'revision'}).encode()).hexdigest()


def fields(state, data):
    due = required(data, 'due', 10)
    try:
        if date.fromisoformat(due).isoformat() != due:
            raise ValueError
    except ValueError as error:
        raise WorkflowError('Informe um prazo válido (AAAA-MM-DD).') from error
    case_ids = data.get('case_ids')
    if (not isinstance(case_ids, list) or len(case_ids) > 50
            or any(not isinstance(identifier, str) for identifier in case_ids)
            or len(set(case_ids)) != len(case_ids)):
        raise WorkflowError('Selecione até 50 casos distintos ou informe uma lista vazia.')
    known = {item['id'] for item in state.get('cases', [])}
    if any(identifier not in known for identifier in case_ids):
        raise WorkflowError('Um dos casos relacionados não existe.')
    return {'title': required(data, 'title', 160), 'description': required(data, 'description', 2000),
            'owner': required(data, 'owner', 80), 'due': due, 'priority': choice(data, 'priority', PRIORITIES),
            'priority_reason': required(data, 'priority_reason'), 'case_ids': list(case_ids)}


def transition(state, command, data):
    normalize(state)
    actor, reason = required(data, 'actor', 80), required(data, 'reason')
    now = utc_now().isoformat(timespec='milliseconds')
    if command == 'work/create':
        require(len(state['work_items']) < MAX_ITEMS, 'Limite local de 2000 trabalhos atingido.')
        item = {**fields(state, data), 'id': f'WRK-{len(state["work_items"]) + 1:03}',
                'status': 'planned', 'created_at': now, 'updated_at': now, 'started_at': None,
                'completed_at': None, 'cancelled_at': None, 'created_by': actor, 'updated_by': actor, 'result': ''}
        item['revision'] = revision(item)
        state['work_items'].append(item)
        return 'Trabalho da segunda linha criado', actor, {**deepcopy(item), 'reason': reason}
    require(command in ('work/update', 'work/status'), 'Ação de trabalho desconhecida.')
    identifier = required(data, 'id', 32)
    item = next((row for row in state['work_items'] if row['id'] == identifier), None)
    require(item is not None, 'Trabalho não encontrado.')
    require(required(data, 'revision', 64) == item['revision'], 'O trabalho mudou. Atualize a página e revise a versão atual.')
    require(item['status'] not in ('completed', 'cancelled'), 'Trabalho encerrado não pode ser alterado.')
    candidate = deepcopy(item)
    if command == 'work/update':
        candidate.update(fields(state, data))
        action = 'Trabalho da segunda linha atualizado'
    else:
        status = choice(data, 'status', ('in_progress', 'completed', 'cancelled'))
        if status == 'in_progress':
            require(item['status'] == 'planned', 'Somente um trabalho planejado pode ser iniciado.')
            candidate['started_at'] = now
        elif status == 'completed':
            require(item['status'] == 'in_progress', 'Inicie o trabalho antes de concluí-lo.')
            candidate['result'] = required(data, 'result', 2000)
            require(datetime.fromisoformat(now) >= datetime.fromisoformat(item['started_at']),
                    'O relógio local está anterior ao início registrado. Confira a data do ambiente.')
            candidate['completed_at'] = now
        else:
            candidate['cancelled_at'] = now
            candidate['cancellation_reason'] = reason
        candidate['status'] = status
        action = {'in_progress': 'Trabalho da segunda linha iniciado', 'completed': 'Trabalho da segunda linha concluído',
                  'cancelled': 'Trabalho da segunda linha cancelado'}[status]
    candidate.update(updated_at=now, updated_by=actor)
    candidate['revision'] = revision(candidate)
    item.clear()
    item.update(candidate)
    return action, actor, {**deepcopy(item), 'reason': reason}


def duration_summary(completed, start_field, definition):
    durations = []
    for item in completed:
        try:
            start, end = datetime.fromisoformat(item[start_field]), datetime.fromisoformat(item['completed_at'])
            if start.tzinfo is None or end.tzinfo is None or end < start:
                continue
            durations.append((end - start).total_seconds())
        except (TypeError, ValueError, KeyError):
            continue
    return {'completed_with_timing': len(durations), 'completed_total': len(completed),
            'mean_seconds': round(sum(durations) / len(durations), 3) if durations else None,
            'median_seconds': round(median(durations), 3) if durations else None,
            'min_seconds': round(min(durations), 3) if durations else None,
            'max_seconds': round(max(durations), 3) if durations else None, 'definition': definition}


def summary(state, now=None):
    require(state.get('audit_valid'), 'Verifique a integridade antes de consultar os indicadores de trabalhos.')
    now = now or utc_now()
    today = now.astimezone(ZoneInfo('America/Sao_Paulo')).date().isoformat()
    items = state.get('work_items', [])
    active = [item for item in items if item['status'] in ('planned', 'in_progress')]
    completed = [item for item in items if item['status'] == 'completed']
    cancelled = [item for item in items if item['status'] == 'cancelled']
    denominator = len(items) - len(cancelled)
    by_priority = []
    for priority in PRIORITIES:
        selected = [item for item in items if item['priority'] == priority]
        pending = [item for item in selected if item['status'] in ('planned', 'in_progress')]
        by_priority.append({'priority': priority, 'total': len(selected), 'pending': len(pending),
            'overdue': sum(item['due'] < today for item in pending),
            'completed': sum(item['status'] == 'completed' for item in selected),
            'cancelled': sum(item['status'] == 'cancelled' for item in selected)})
    return {'operations': overview(state, now), 'as_of': now.isoformat(timespec='milliseconds'), 'today': today, 'timezone': 'America/Sao_Paulo',
            'total': len(items), 'status_counts': {status: sum(item['status'] == status for item in items) for status in STATUSES},
            'pending': len(active), 'overdue': sum(item['due'] < today for item in active), 'by_priority': by_priority,
            'completion_rate': {'numerator': len(completed), 'denominator': denominator,
                'percent': round(100 * len(completed) / denominator, 2) if denominator else None,
                'definition': 'Trabalhos concluídos / todos os trabalhos não cancelados.'},
            'treatment_time': duration_summary(completed, 'started_at', 'Tempo corrido entre início e conclusão; somente concluídos com datas válidas. Inclui períodos sem atividade e não representa horas trabalhadas.'),
            'lead_time': duration_summary(completed, 'created_at', 'Tempo corrido entre criação e conclusão; somente concluídos com datas válidas.'),
            'scope': 'Trabalhos locais da segunda linha, independentes dos planos de ação de casos. Pendente = planejado ou em andamento; atraso = prazo anterior ao dia atual em São Paulo. Não mede benefício causal nem resultado de IA.'}
