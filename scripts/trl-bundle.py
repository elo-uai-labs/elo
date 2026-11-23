"""Package only explicitly selected synthetic evidence, never secrets or a database."""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import zipfile
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/trl5'
REQUIRED = ['docs/trl5/ambiente-relevante.md', 'docs/trl5/execucao.md', 'docs/trl5/conclusao.md',
            'docs/trl-source-integration.md', 'docs/trl-operation.md', 'docs/trl-evaluation.md',
            'docs/reviews/general-trl5.md', 'docs/reviews/security-trl5.md',
            'docs/reviews/dba-trl5.md', 'docs/reviews/performance-trl5.md',
            'output/validation/trl5/source-integration.json', 'output/validation/trl-operation.json',
            'output/validation/trl5/acceptance.json',
            'output/validation/trl-evaluation-ai-first/report.json',
            'output/validation/trl-evaluation-ai-first/independent-review.json',
            'output/validation/trl-evaluation-ai-first/adjudicated.json',
            'output/validation/trl-evaluation-ocr-first/report.json',
            'output/validation/trl-evaluation-regression-1/report.json',
            'output/validation/trl-evaluation-regression-1/independent-review.json',
            'output/validation/trl-evaluation-regression-1/adjudicated.json']


def sha(content):
    return hashlib.sha256(content).hexdigest()


def main():
    names = REQUIRED + [str(p.relative_to(ROOT)) for p in sorted((ROOT/'tests/fixtures/trl-evaluation').iterdir()) if p.is_file()]
    files = {}
    for name in names:
        path = ROOT / name
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(ROOT):
            raise ValueError(f'Arquivo obrigatório ausente ou link: {name}')
        content = path.read_bytes()
        if re.search(rb'sk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{40,}', content):
            raise ValueError(f'Possível segredo: {name}')
        files[name] = content
    git = lambda *args: subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()
    code_paths = [name for name in git('ls-files').splitlines() if name.startswith(('backend/', 'scripts/', 'tests/', 'src/')) and (ROOT/name).is_file()]
    manifest = {'version': 'elo-trl-evidence-bundle-v1', 'created_at': datetime.now(timezone.utc).isoformat(),
                'commit': git('rev-parse', 'HEAD'), 'working_tree_dirty': bool(git('status', '--porcelain')),
                'scope': 'Synthetic technical evidence; original failures retained. No automatic TRL assignment, corporate or human validation.',
                'files': {name: {'sha256': sha(data), 'bytes': len(data)} for name, data in files.items()},
                'code_sha256_not_bundled': {name: sha((ROOT/name).read_bytes()) for name in code_paths}}
    raw = (json.dumps(manifest, ensure_ascii=False, indent=2)+'\n').encode()
    OUT.mkdir(parents=True, exist_ok=True)
    destination = OUT/'elo-evidencias-trl5.zip'
    with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
        archive.writestr('manifesto.json', raw)
    with zipfile.ZipFile(destination) as archive:
        assert archive.testzip() is None
        assert set(archive.namelist()) == set(files) | {'manifesto.json'}
        for name, data in files.items():
            assert sha(archive.read(name)) == sha(data)
    (OUT/'manifesto.json').write_bytes(raw)
    summary = {'file': destination.name, 'sha256': sha(destination.read_bytes()), 'files': len(files),
               'commit': manifest['commit'], 'working_tree_dirty': manifest['working_tree_dirty']}
    (OUT/'resumo.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
