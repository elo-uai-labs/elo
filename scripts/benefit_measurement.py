"""Offline paired task measurement. Never connects to Elo or infers human results."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from statistics import median

FIELDS = ['pair_id', 'participant_id', 'task_id', 'sample_sha256', 'phase',
          'order', 'human_minutes', 'wait_minutes', 'corrections',
          'required_facts', 'complete_facts', 'evidence', 'synthetic']


def summarize(rows):
    pairs = {}
    for number, raw in enumerate(rows, 2):
        if any(not str(raw.get(k, '')).strip() for k in FIELDS):
            raise ValueError(f'Linha {number}: campos obrigatórios vazios')
        row = dict(raw)
        if row['phase'] not in ('baseline', 'elo') or row['order'] not in ('1', '2'):
            raise ValueError(f'Linha {number}: fase ou ordem inválida')
        if row['synthetic'] not in ('true', 'false'):
            raise ValueError(f'Linha {number}: synthetic deve ser true/false')
        if len(row['sample_sha256']) != 64 or any(c not in '0123456789abcdef' for c in row['sample_sha256']):
            raise ValueError(f'Linha {number}: hash inválido')
        for field in ('human_minutes', 'wait_minutes', 'corrections', 'required_facts', 'complete_facts'):
            value = float(row[field])
            if not math.isfinite(value) or value < 0:
                raise ValueError(f'Linha {number}: medida inválida {field}')
            if field in ('corrections', 'required_facts', 'complete_facts') and not value.is_integer():
                raise ValueError(f'Linha {number}: contagem deve ser inteira')
            row[field] = value
        if row['complete_facts'] > row['required_facts'] or not row['required_facts']:
            raise ValueError(f'Linha {number}: denominador/completude inválidos')
        pair = pairs.setdefault(row['pair_id'], {})
        if row['phase'] in pair:
            raise ValueError(f'Par duplicado: {row["pair_id"]}/{row["phase"]}')
        pair[row['phase']] = row
    results, incomplete = [], []
    for key, pair in pairs.items():
        if len(pair) != 2:
            incomplete.append(key)
            continue
        baseline, elo = pair['baseline'], pair['elo']
        for field in ('participant_id', 'task_id', 'sample_sha256', 'required_facts', 'synthetic'):
            if baseline[field] != elo[field]:
                raise ValueError(f'Par {key}: {field} não comparável')
        if baseline['order'] == elo['order']:
            raise ValueError(f'Par {key}: ordem duplicada')
        saved = baseline['human_minutes'] - elo['human_minutes']
        results.append({'pair_id': key, 'synthetic': baseline['synthetic'] == 'true',
                        'first_phase': 'baseline' if baseline['order'] == '1' else 'elo',
                        'human_minutes_saved': saved,
                        'reduction_percent': saved / baseline['human_minutes'] * 100 if baseline['human_minutes'] else None,
                        'corrections_delta': elo['corrections'] - baseline['corrections'],
                        'completeness_delta': (elo['complete_facts'] - baseline['complete_facts']) / baseline['required_facts'],
                        'baseline': baseline, 'elo': elo})
    groups = {}
    for synthetic in (True, False):
        items = [r for r in results if r['synthetic'] == synthetic]
        groups['synthetic' if synthetic else 'participant_recorded'] = {
            'pairs': len(items),
            'median_human_minutes_saved': median([r['human_minutes_saved'] for r in items]) if items else None,
            'completeness_worsened_pairs': sum(r['completeness_delta'] < 0 for r in items),
            'baseline_first_pairs': sum(r['first_phase'] == 'baseline' for r in items),
            'elo_first_pairs': sum(r['first_phase'] == 'elo' for r in items),
        }
    return {'schema': 'elo-benefit-v1', 'groups': groups, 'paired_results': results,
            'incomplete_pair_ids': incomplete,
            'limits': 'Registros declarados pelo operador; não verifica evidências nem homologa benefício. Tempos ativos e espera separados. Pares incompletos excluídos. Ordem pode introduzir aprendizagem. Dados sintéticos não estimam ganho real.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        data = args.input.read_bytes()
        with args.input.open(newline='', encoding='utf-8-sig') as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames != FIELDS:
                raise ValueError('Cabeçalho deve corresponder ao modelo benefit-template.csv')
            report = summarize(list(reader))
        report['input_sha256'] = hashlib.sha256(data).hexdigest()
        with args.output.open('x', encoding='utf-8') as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write('\n')
    except (ValueError, OSError) as error:
        parser.exit(1, f'Erro: {error}\n')


if __name__ == '__main__':
    main()
