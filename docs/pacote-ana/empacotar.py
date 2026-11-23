"""Build a local review bundle using an explicit non-secret allowlist."""
from pathlib import Path
import hashlib
import json
import subprocess
import zipfile
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'output/pacote-ana'
BASE = ['README.md', 'docs/design-system.md', 'docs/entrega.md',
        'docs/diagnostico-ana-2026-11-23.md', 'docs/pilot-experiment.md',
        'docs/pilot-onboarding.md', 'docs/cost-model.csv', 'docs/ocr.md',
        'docs/access.md', 'docs/operations.md', 'docs/monitoring.md',
        'docs/security-readiness.md', 'docs/edital-execution.md', 'docs/product-vision.md']
OPTIONAL = ['docs/reviews/general-parallel.md', 'docs/reviews/security-parallel.md',
            'docs/reviews/dba-parallel.md', 'docs/reviews/performance-parallel.md',
            'output/validation/result-local.json', 'output/validation/repeated.json',
            'output/validation/repeated-real.json', 'output/validation/performance-parallel.json',
            'output/validation/dba-parallel.json', 'output/validation/parallel-acceptance.json', 'output/pacote-ana/anexos-validacao.json','docs/avaliacao-ia-ocr.md', 'docs/operacao-equipes.md',
            'docs/tipologia-perfil-repetido.md', 'docs/runtime-local.md',
            'output/validation/result-real.json', 'output/validation/result-auth.json',
            'output/validation/openai-assistant-real.json',
            'output/validation/ocr-quality.json', 'output/validation/ocr-performance.json',
            'output/validation/operations-e2e.json',
            'output/validation/evaluation/real.json', 'output/validation/evaluation/ocr.json',
            'output/validation/evaluation/adjudicated.json',
            'output/validation/evaluation/independent-review.json']


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()


def digest(content):
    return hashlib.sha256(content).hexdigest()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    names = BASE + [str(p.relative_to(ROOT)) for p in sorted((ROOT/'docs/pacote-ana').glob('*')) if p.is_file()]
    names += [str(p.relative_to(ROOT)) for p in sorted((ROOT/'docs/demo').glob('*')) if p.is_file()]
    for sub in ('modelos-originais', 'anexos-trabalho'):
        names += [str(p.relative_to(ROOT)) for p in sorted((OUT/sub).glob('*.xlsx')) if p.is_file()]
    names += [name for name in OPTIONAL if (ROOT/name).is_file()]
    files = {}
    for name in sorted(set(names)):
        path = ROOT/name
        if path.is_symlink() or not path.is_file():
            raise ValueError(f'Arquivo obrigatório ausente ou link: {name}')
        data = path.read_bytes()
        # Key patterns must never appear in the distributable payload.
        import re
        if re.search(rb'sk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{40,}', data):
            raise ValueError(f'Possível segredo: {name}')
        files[name] = data
    code = {}
    for name in git('ls-files', '--cached', '--others', '--exclude-standard').splitlines():
        if name.startswith(('backend/', 'src/', 'scripts/', 'tests/')) or name in ('package.json', 'package-lock.json', 'vite.config.js'):
            p = ROOT/name
            if p.is_file() and not p.is_symlink(): code[name] = digest(p.read_bytes())
    manifest = {'created_at': datetime.now(timezone.utc).isoformat(),
                'scope': 'Local review only; synthetic data; no submission or corporate approval.',
                'base_commit': git('rev-parse', 'HEAD'), 'branch': git('branch', '--show-current'),
                'working_tree_dirty': bool(git('status', '--porcelain')),
                'files': {n: {'sha256': digest(b), 'bytes':len(b)} for n,b in files.items()},
                'code_hashes_not_bundled': code,
                'optional_missing': [n for n in OPTIONAL if not (ROOT/n).is_file()],
                'evidence_note': 'Artifact dates and scope must be inspected; inclusion is not a new test result.'}
    raw = (json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode()
    (OUT/'manifesto.json').write_bytes(raw)
    dest = OUT/'elo-revisao-ana.zip'
    with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED) as archive:
        for name,data in files.items(): archive.writestr(name,data)
        archive.writestr('manifesto.json',raw)
    with zipfile.ZipFile(dest) as archive:
        assert archive.testzip() is None
        for name,data in files.items(): assert digest(archive.read(name)) == digest(data)
    summary = {'archive':dest.name, 'sha256':digest(dest.read_bytes()), 'files':len(files),
               'manifest_sha256':digest(raw),'base_commit':manifest['base_commit'],
               'working_tree_dirty':manifest['working_tree_dirty']}
    (OUT/'resumo.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(summary,ensure_ascii=False))


if __name__ == '__main__': main()
