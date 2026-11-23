#!/usr/bin/env python3
"""Short isolated CPU attribution; not HTTP load or a capacity acceptance test."""
import cProfile
import importlib.util
import json
from pathlib import Path
import pstats
import tempfile
import time

spec = importlib.util.spec_from_file_location('capacity', Path(__file__).with_name('capacity-local.py'))
capacity = importlib.util.module_from_spec(spec)
spec.loader.exec_module(capacity)


def profile(function):
    profiler = cProfile.Profile()
    began = time.perf_counter()
    for _ in range(5):
        profiler.runcall(function)
    elapsed = time.perf_counter() - began
    stats = pstats.Stats(profiler)
    rows = []
    for (filename, line, name), (primitive, calls, internal, cumulative, _) in sorted(
            stats.stats.items(), key=lambda entry: entry[1][3], reverse=True)[:18]:
        rows.append({'file': Path(filename).name, 'line': line, 'function': name,
                     'calls': calls, 'internal_seconds': internal, 'cumulative_seconds': cumulative})
    return {'iterations': 5, 'wall_seconds_including_profiler': elapsed, 'top_cumulative': rows}


with tempfile.TemporaryDirectory(prefix='elo-capacity-profile-') as folder:
    store = capacity.Store(Path(folder) / 'profile.sqlite3')
    capacity.seed(store, 2000)
    ledger = capacity.AccessAudit(store.path)
    def append():
        ledger.append(actor='capacity-profile', mode='local-service', event='read',
                      target='/api/state', outcome='success', ip='127.0.0.1')
    for _ in range(2000):
        append()
    before = store.export_state()
    result = {'scope': 'Five isolated calls each, with cProfile overhead; no contention/HTTP/production claim',
              'contracts': 2000, 'cases': len(before['cases']), 'initial_access_events': 2000,
              'store_read': profile(store.read), 'access_append': profile(append)}
    result['business_unchanged'] = capacity.digest(before) == capacity.digest(store.export_state())
    result['access_valid'] = capacity.verify_package(ledger.export())
    result['source_hashes'] = {str(path.relative_to(capacity.ROOT)): capacity.hashlib.sha256(path.read_bytes()).hexdigest()
                               for path in sorted((capacity.ROOT / 'backend').glob('*.py'))}
output = capacity.ROOT / 'output/validation/capacity-profile.json'
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'output': str(output), 'read_seconds': result['store_read']['wall_seconds_including_profiler'],
                  'append_seconds': result['access_append']['wall_seconds_including_profiler']}))
