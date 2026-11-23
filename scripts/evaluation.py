"""Bounded synthetic evaluation. Metrics are proxies unless separately adjudicated."""
import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import time
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
FIXTURES = ROOT / 'tests/fixtures/evaluation/ai.json'


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def ratio(numerator, denominator):
    return {'numerator': numerator, 'denominator': denominator,
            'rate': numerator / denominator if denominator else None}


def score(case, result):
    claims = result['claims']
    valid = sum(bool(c['source_ids']) and set(c['source_ids']) <= {s['id'] for s in case['sources']} for c in claims)
    hits = []
    for fact in case['facts']:
        # A lexical anchor counts only when attached to all required sources.
        cited_text = ' '.join(c['text'] for c in claims if set(fact['source_ids']) <= set(c['source_ids']))
        hits.append({'id': fact['id'], 'matched': all(re.search(p, cited_text, re.I) for p in fact['patterns'])})
    return {'valid_reference_claims': ratio(valid, len(claims)),
            'anchor_coverage': ratio(sum(h['matched'] for h in hits), len(hits)),
            'facts': hits, 'abstained': not bool(claims),
            'abstention_matches_expected': (not bool(claims)) == case['abstain'],
            'semantic_support': 'pending_independent_review',
            'warning': 'Referência válida e âncora lexical não provam sustentação, completude ou ausência de contradição.'}


def distance(expected, actual):
    previous = list(range(len(actual) + 1))
    for i, left in enumerate(expected, 1):
        current = [i]
        for j, right in enumerate(actual, 1):
            current.append(min(current[-1] + 1, previous[j] + 1, previous[j-1] + (left != right)))
        previous = current
    return previous[-1]


def normalize(text):
    return ' '.join(unicodedata.normalize('NFC', text).split())


def summary(rows):
    times = sorted(r['seconds'] for r in rows)
    success = [r for r in rows if r['status'] == 'ok']
    return {'requests': len(rows), 'failures': len(rows)-len(success),
            'latency_seconds': {'p50': times[math.ceil(len(times)*.5)-1] if times else None,
                                'p95': times[math.ceil(len(times)*.95)-1] if times else None,
                                'max': max(times) if times else None},
            'abstention_accuracy_proxy': ratio(sum(r['metrics']['abstention_matches_expected'] for r in success), len(rows)),
            'valid_references': ratio(sum(r['metrics']['valid_reference_claims']['numerator'] for r in success), sum(r['metrics']['valid_reference_claims']['denominator'] for r in success)),
            'anchor_coverage_proxy': ratio(sum(r['metrics']['anchor_coverage']['numerator'] for r in success), sum(r['metrics']['anchor_coverage']['denominator'] for r in success))}


def evaluate_ai():
    import dossier
    import consultation
    fixture = json.loads(FIXTURES.read_text())
    if not dossier.configured() or dossier.provider() != 'openai':
        raise RuntimeError('Configure OpenAI no .env; avaliação não troca de provedor.')
    rows = []
    for case in fixture['cases']:
        started = time.monotonic()
        row = {'id': case['id'], 'case': case}
        try:
            if case['mode'] == 'assistant':
                result = dossier.generate_grounded(case['sources'], consultation.INSTRUCTIONS, case['question'])
            else:
                result = dossier.generate_real(case['sources'], [s['id'] for s in case['sources']])
            row.update(status='ok', result=result, response_sha256=digest(result), metrics=score(case, result))
        except Exception as error:
            # Do not serialize exception strings, which may carry transport secrets.
            row.update(status='failed', error_type=type(error).__name__)
        row['seconds'] = round(time.monotonic()-started, 4)
        rows.append(row)
        print(f"{case['id']}: {row['status']}", flush=True)
    return {'fixture_version': fixture['version'], 'fixture_sha256': digest(fixture), 'rows': rows, 'summary': summary(rows)}


def evaluate_ocr():
    import ocr
    sys.path.insert(0, str(ROOT / 'backend/tests'))
    from ocr_fixtures import build_fixtures, EXPECTED_TEXT
    fixtures = build_fixtures()
    rows = []
    for name, mime, expected, inconclusive in [
        ('png','image/png',EXPECTED_TEXT,False), ('jpeg','image/jpeg',EXPECTED_TEXT,False),
        ('pdf','application/pdf',EXPECTED_TEXT,False), ('blank','image/png','',True),
        ('degraded','image/png',EXPECTED_TEXT,True),
        ('portuguese','image/png','AÇÃO DE REVISÃO\nCONTRATO SINTÉTICO\nFORNECEDOR FICTÍCIO',False)]:
        content = base64.b64decode(fixtures[name])
        started = time.monotonic()
        result = ocr.extract(content, mime)
        recognized = '\n'.join(segment['text'] for segment in result['segments'])
        ref, actual = normalize(expected), normalize(recognized)
        rows.append({'id': name, 'input_sha256':hashlib.sha256(content).hexdigest(),
                     'expected_text':expected, 'actual_text':recognized,
                     'character_errors':distance(ref, actual), 'reference_characters':len(ref),
                     'cer':distance(ref, actual)/len(ref) if ref else None,
                     'expected_inconclusive':inconclusive, 'extraction_status':result['extraction_status'],
                     'triage_matches_expected':(result['extraction_status']=='inconclusive')==inconclusive,
                     'seconds':round(time.monotonic()-started,4), 'engine':result['engine'],
                     'segments':result['segments'], 'quality':result['quality']})
    legible=[r for r in rows if not r['expected_inconclusive']]
    return {'rows':rows,'summary':{'legible_cer':ratio(sum(r['character_errors'] for r in legible),sum(r['reference_characters'] for r in legible)),
            'triage':ratio(sum(r['triage_matches_expected'] for r in rows),len(rows)),
            'blank_false_characters':sum(len(normalize(r['actual_text'])) for r in rows if not r['expected_text'])},
            'normalization':'Unicode NFC e espaços consecutivos colapsados; acentos e caixa preservados.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--real', action='store_true', help='Executa exatamente oito chamadas reais potencialmente cobradas.')
    parser.add_argument('--ocr', action='store_true', help='Executa seis fixtures de OCR local.')
    args=parser.parse_args()
    if not args.real and not args.ocr: parser.error('Escolha --real e/ou --ocr; sem chamada implícita.')
    report={'version':'elo-evaluation-v1','created_at':datetime.now(timezone.utc).isoformat(),
            'scope':'Dados sintéticos; não estima precisão corporativa. Sem acesso ao banco.',
            'code_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ['backend/dossier.py','backend/consultation.py','backend/ocr.py','scripts/evaluation.py']}}
    if args.real: report['ai']=evaluate_ai()
    if args.ocr: report['ocr']=evaluate_ocr()
    output=ROOT/'output/validation/evaluation'
    output.mkdir(parents=True,exist_ok=True)
    path=output/('real-ocr.json' if args.real and args.ocr else 'real.json' if args.real else 'ocr.json')
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(path)
    if args.real and report['ai']['summary']['failures']: return 1
    return 0


if __name__=='__main__':
    raise SystemExit(main())
