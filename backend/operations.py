"""Read-only local operating alerts; no deliveries, decisions or acknowledged state."""
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

TZ = ZoneInfo('America/Sao_Paulo')


def overview(state, now):
    today = now.astimezone(TZ).date()
    horizon = today + timedelta(days=7)
    notifications = []
    work = state.get('work_items', [])
    for kind, items, closed in (('work', work, ('completed', 'cancelled')),
                                 ('action', state.get('actions', []), ('done',))):
        for item in items:
            if item['status'] in closed:
                continue
            due = date.fromisoformat(item['due'])
            if due <= horizon:
                status = 'overdue' if due < today else 'due_today' if due == today else 'due_soon'
                notifications.append({'id': f'{kind}:{item["id"]}:deadline', 'kind': status,
                    'entity_type': kind, 'entity_id': item['id'], 'case_id': item.get('case_id'),
                    'title': item['title'], 'owner': item['owner'], 'due': due.isoformat(),
                    'days_to_due': (due - today).days})
            if kind == 'action' and item['status'] == 'closure_requested':
                notifications.append({'id': f'action:{item["id"]}:review', 'kind': 'closure_review',
                    'entity_type': kind, 'entity_id': item['id'], 'case_id': item['case_id'],
                    'title': item['title'], 'owner': item['owner'], 'due': due.isoformat(),
                    'days_to_due': (due - today).days})
    order = {'overdue': 0, 'closure_review': 1, 'due_today': 2, 'due_soon': 3}
    notifications.sort(key=lambda row: (order[row['kind']], row['due'], row['id']))
    completed = [item for item in work if item['status'] == 'completed']
    evaluable, on_time = 0, 0
    for item in completed:
        try:
            finished = datetime.fromisoformat(item['completed_at'])
            if finished.tzinfo is None:
                continue
            due = date.fromisoformat(item['due'])
        except (KeyError, TypeError, ValueError):
            continue
        evaluable += 1
        on_time += finished.astimezone(TZ).date() <= due
    groups = {}
    for case in state.get('cases', []):
        contract = case.get('records', {}).get('contract', {})
        sources = {source.get('id') for source in case.get('evidence', [])}
        if not contract.get('id') or contract['id'] not in sources or not contract.get('supplier_id'):
            continue
        rule = case.get('rule', {}).get('id', 'legacy')
        key = (rule, contract['supplier_id'])
        group = groups.setdefault(key, {'rule_id': rule, 'supplier_id': contract['supplier_id'],
                                      'contract_ids': set(), 'case_ids': []})
        group['contract_ids'].add(contract['id'])
        group['case_ids'].append(case['id'])
    recurring = [{**group, 'contract_ids': sorted(group['contract_ids']), 'case_ids': sorted(group['case_ids']),
                  'distinct_contracts': len(group['contract_ids'])} for group in groups.values() if len(group['contract_ids']) >= 2]
    recurring.sort(key=lambda row: (-row['distinct_contracts'], row['rule_id'], row['supplier_id']))
    return {'version': 'elo-operations-v1', 'notification_total': len(notifications), 'notifications': notifications,
        'notice': 'Avisos locais calculados ao carregar ou atualizar. Janela: hoje e os próximos 7 dias corridos; não são enviados por email nem em segundo plano. Encerramento de plano exige revisão independente.',
        'sla': {'on_time': on_time, 'evaluated': evaluable, 'completed': len(completed),
                'missing_timestamp': len(completed) - evaluable,
                'percent': round(100 * on_time / evaluable, 2) if evaluable else None,
                'definition': 'SLA local: trabalhos concluídos até o fim do prazo vigente em São Paulo / concluídos com data válida. Cancelados e pendentes fora do denominador. Alterações justificadas de prazo mudam a referência; não mede o prazo original nem horas trabalhadas.'},
        'recurrence': {'groups': recurring, 'definition': 'Mesmo fornecedor e mesma regra em pelo menos dois contratos distintos com origem evidenciada, em todo o histórico local. Não demonstra reincidência de irregularidade nem soma sinais do mesmo contrato.'}}
