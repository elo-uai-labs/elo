"""Generate synthetic OCR fixtures using local macOS graphics; stdlib only."""
import json
from pathlib import Path
import subprocess
import tempfile

EXPECTED_TEXT = 'ELO TESTE SINTETICO\nCTR-1042 FOR-031\nTOTAL 12345'


def build_fixtures():
    with tempfile.TemporaryDirectory(prefix='elo-ocr-fixtures-') as temp:
        executable = str(Path(temp) / 'fixtures')
        subprocess.run(['swiftc', str(Path(__file__).with_suffix('.swift')), '-o', executable],
                       check=True, stdout=subprocess.DEVNULL, timeout=60)
        return json.loads(subprocess.check_output([executable], timeout=15))


if __name__ == '__main__':
    print(json.dumps(build_fixtures()))
