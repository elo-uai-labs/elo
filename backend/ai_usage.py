"""Provider-reported token metadata and estimates; never an invoice ledger."""
import argparse
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path

FIELDS = ('input_tokens', 'cached_input_tokens', 'output_tokens', 'reasoning_tokens', 'total_tokens')


def openai_usage(raw):
    result = {'provider': 'openai', 'status': 'missing', **dict.fromkeys(FIELDS)}
    if raw is None:
        return result
    if not isinstance(raw, dict):
        return {**result, 'status': 'invalid'}
    values = {key: raw.get(key) for key in ('input_tokens', 'output_tokens', 'total_tokens')}
    for parent, field, child in (('input_tokens_details', 'cached_input_tokens', 'cached_tokens'),
                                 ('output_tokens_details', 'reasoning_tokens', 'reasoning_tokens')):
        detail = raw.get(parent)
        if detail is not None and not isinstance(detail, dict):
            return {**result, 'status': 'invalid'}
        values[field] = detail.get(child) if detail else None
    if any(value is not None and (type(value) is not int or not 0 <= value <= 10**12) for value in values.values()):
        return {**result, 'status': 'invalid'}
    for subset, total in (('cached_input_tokens', 'input_tokens'), ('reasoning_tokens', 'output_tokens')):
        if values[subset] is not None and values[total] is not None and values[subset] > values[total]:
            return {**result, 'status': 'invalid'}
    if all(values[k] is not None for k in ('input_tokens', 'output_tokens', 'total_tokens')) and values['total_tokens'] != values['input_tokens'] + values['output_tokens']:
        return {**result, 'status': 'invalid'}
    return {**result, **values, 'status': 'complete' if all(v is not None for v in values.values()) else 'partial'}


def valid_usage(value):
    if not isinstance(value, dict) or set(value) != {'provider', 'status', *FIELDS} or value.get('provider') != 'openai':
        return False
    if value['status'] in ('missing', 'invalid'):
        return all(value[key] is None for key in FIELDS)
    rebuilt = openai_usage({**{key: value[key] for key in ('input_tokens', 'output_tokens', 'total_tokens')},
                           'input_tokens_details': {'cached_tokens': value['cached_input_tokens']},
                           'output_tokens_details': {'reasoning_tokens': value['reasoning_tokens']}})
    return value == rebuilt


def validate_rates(rates):
    if not isinstance(rates, dict):
        raise ValueError('Tarifas devem ser um objeto por modelo.')
    for model, rate in rates.items():
        if not isinstance(model, str) or not isinstance(rate, dict) or set(rate) != {'currency', 'input_per_million', 'cached_input_per_million', 'output_per_million'}:
            raise ValueError('Tarifa exige modelo, currency e três preços por milhão.')
        if not isinstance(rate['currency'], str) or len(rate['currency']) != 3 or not rate['currency'].isascii() or not rate['currency'].isalpha():
            raise ValueError('Moeda deve ter três letras.')
        for key in ('input_per_million', 'cached_input_per_million', 'output_per_million'):
            try:
                amount = Decimal(str(rate[key]))
            except (InvalidOperation, ValueError):
                raise ValueError('Preço inválido.') from None
            if not amount.is_finite() or amount < 0:
                raise ValueError('Preço deve ser finito e não negativo.')


def summarize(events, rates=None):
    rates = {} if rates is None else rates
    validate_rates(rates)
    rows = []
    for event in events:
        if event.get('action') not in ('Dossiê registrado', 'Consulta ao assistente registrada'):
            continue
        detail = event['details']
        usage = detail.get('usage')
        if usage is not None and not valid_usage(usage):
            raise ValueError('Metadados de consumo inválidos no pacote.')
        row = {'event_seq': event['seq'], 'at': event['at'], 'kind': 'dossier' if event['action'] == 'Dossiê registrado' else 'assistant',
               'case_id': detail.get('case_id'), 'model': detail.get('model'), 'mode': detail.get('mode'),
               'usage': usage, 'estimated_cost': None, 'currency': None}
        rate = rates.get(row['model'])
        if rate and usage and all(usage[key] is not None for key in ('input_tokens', 'cached_input_tokens', 'output_tokens')):
            cost = ((usage['input_tokens'] - usage['cached_input_tokens']) * Decimal(str(rate['input_per_million']))
                    + usage['cached_input_tokens'] * Decimal(str(rate['cached_input_per_million']))
                    + usage['output_tokens'] * Decimal(str(rate['output_per_million']))) / Decimal(1000000)
            row.update(estimated_cost=str(cost), currency=rate['currency'].upper())
        rows.append(row)
    totals = {key: {'reported_sum': sum(row['usage'][key] for row in rows if row['usage'] and row['usage'][key] is not None),
                    'measured_records': sum(bool(row['usage'] and row['usage'][key] is not None) for row in rows),
                    'unmeasured_records': sum(not row['usage'] or row['usage'][key] is None for row in rows)} for key in FIELDS}
    currencies = {row['currency'] for row in rows if row['estimated_cost'] is not None}
    return {'format': 'elo-ai-usage-v1', 'scope': 'Somente respostas persistidas na trilha; chamadas falhadas, rejeitadas ou não gravadas não estão contabilizadas. Ausência não é zero. Não reconcilia fatura.',
            'records': rows, 'totals': totals, 'rates_supplied': rates,
            'estimated_cost_by_currency': {currency: str(sum((Decimal(row['estimated_cost']) for row in rows if row['currency'] == currency), Decimal(0))) for currency in sorted(currencies)},
            'records_without_cost_estimate': sum(row['estimated_cost'] is None for row in rows)}


def main():
    parser = argparse.ArgumentParser(description='Consumo de respostas persistidas em pacote de auditoria verificado; não acessa banco nem API.')
    parser.add_argument('package', type=Path)
    parser.add_argument('--rates', type=Path, help='JSON de tarifas explícitas por modelo, sem valores padrão.')
    args = parser.parse_args()
    from audit_export import verify_export
    try:
        package = json.loads(args.package.read_text())
        if not verify_export(package):
            raise ValueError('Pacote de auditoria inválido.')
        rates = json.loads(args.rates.read_text()) if args.rates else None
        print(json.dumps(summarize(package['events'], rates), ensure_ascii=False, indent=2))
    except (OSError, ValueError, KeyError, TypeError):
        parser.exit(2, 'Não foi possível verificar o pacote ou as tarifas. Confira os arquivos de entrada.\n')


if __name__ == '__main__':
    main()
