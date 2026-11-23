"""Opt-in local OCR boundary. No network, decisions or database writes.

Tesseract confidence is an internal heuristic, not measured accuracy. Accepted OCR
still requires the caller's explicit human review of the source and locations.
"""
import hashlib
import csv
import io
import shutil
import tempfile
import time
import json
import math
import os
from pathlib import Path
import subprocess

from domain import WorkflowError

VERSION = 'elo-tesseract-ocr-v1'
MAX_BYTES = 1024 * 1024
MAX_TEXT_BYTES = 32768
MAX_SEGMENTS = 500
MAX_PAGES = 5
MAX_PIXELS = 12_000_000
TIMEOUT_SECONDS = 30
CONFIDENCE_THRESHOLD = 0.8
MODELS = json.loads(Path(__file__).with_name('ocr_models.json').read_text())
MODEL_DIRECTORY = Path(__file__).resolve().parents[1] / '.local' / 'tessdata'
CONFIDENCE_NOTE = 'Escore interno do Tesseract, não probabilidade de acerto nem precisão medida. Limiar provisório de triagem; revisão humana obrigatória.'
LIMITATIONS = ('OCR local experimental: pode omitir ou confundir caracteres mesmo com escore alto. '
    'Confira texto, página e região no original antes de usar. Coordenadas normalizadas de 0 a 1, '
    'origem superior esquerda após orientação EXIF; no PDF, relativas à página rasterizada. '
    'Sem inferência de vínculo, decisão automática ou serviço externo.')


def binary_path():
    return Path(os.environ.get('ELO_OCR_BIN') or Path(__file__).resolve().parents[1] / '.local' / 'elo-ocr')


def _executable(path):
    return bool(path) and Path(path).is_file() and os.access(path, os.X_OK)


def tesseract_path():
    # An explicit override is never silently replaced by a different installation.
    if 'ELO_TESSERACT_BIN' in os.environ:
        return os.environ['ELO_TESSERACT_BIN']
    discovered = shutil.which('tesseract')
    if discovered:
        return discovered
    return next((path for path in ('/opt/homebrew/bin/tesseract', '/usr/local/bin/tesseract')
                 if _executable(path)), None)


def configured():
    path = binary_path()
    return path.is_file() and os.access(path, os.X_OK) and _executable(tesseract_path()) and all((MODEL_DIRECTORY / f'{language}.traineddata').is_file() for language in MODELS['models'])


def _inconclusive(code, engine=None):
    return {'text': '', 'segments': [], 'missing_pages': [], 'pages': [],
        'extraction_status': 'inconclusive', 'engine': engine or {'name': 'Tesseract', 'version': VERSION},
        'quality': {'assessment': 'inconclusive', 'minimum_confidence': None, 'mean_confidence': None,
                    'threshold': CONFIDENCE_THRESHOLD, 'confidence_note': CONFIDENCE_NOTE, 'flags': [code]},
        'limitations': LIMITATIONS}


def _number(value):
    return type(value) in (int, float) and math.isfinite(value)


def _validate(result):
    """Validate worker structure and derive triage; this does not verify text truth."""
    if not isinstance(result, dict):
        raise ValueError('shape')
    segments, pages, missing, engine = (result.get(key) for key in ('segments', 'pages', 'missing_pages', 'engine'))
    if not isinstance(pages, list) or not 1 <= len(pages) <= MAX_PAGES:
        raise ValueError('pages')
    page_ids = set()
    for page in pages:
        if not isinstance(page, dict) or type(page.get('page')) is not int or page['page'] in page_ids:
            raise ValueError('page')
        if any(type(page.get(key)) is not int or not 1 <= page[key] <= 12000 for key in ('width', 'height')):
            raise ValueError('pixels')
        if page['width'] * page['height'] > MAX_PIXELS:
            raise ValueError('pixels')
        page_ids.add(page['page'])
    if page_ids != set(range(1, len(pages) + 1)):
        raise ValueError('pages')
    if not isinstance(missing, list) or any(type(page) is not int for page in missing) or not set(missing) <= page_ids or len(missing) != len(set(missing)):
        raise ValueError('missing')
    if not isinstance(engine, dict) or engine.get('name') != 'Tesseract' or engine.get('version') != VERSION:
        raise ValueError('engine')
    if not isinstance(engine.get('os'), str) or len(engine['os']) > 200 or engine.get('languages') != ['por', 'eng'] or not isinstance(engine.get('runtime_version'), str):
        raise ValueError('engine')
    if not isinstance(segments, list) or len(segments) > MAX_SEGMENTS:
        raise ValueError('segments')
    cleaned = []
    for segment in segments:
        if not isinstance(segment, dict) or type(segment.get('page')) is not int or segment['page'] not in page_ids:
            raise ValueError('segment page')
        text = segment.get('text')
        if not isinstance(text, str) or not text.strip() or any(ord(char) < 32 and char not in '\t\n\r' for char in text):
            raise ValueError('text')
        confidence, bounds = segment.get('confidence'), segment.get('bbox')
        if not _number(confidence) or not 0 <= confidence <= 1 or not isinstance(bounds, dict):
            raise ValueError('confidence')
        if set(bounds) != {'x', 'y', 'width', 'height'} or any(not _number(value) or not 0 <= value <= 1 for value in bounds.values()):
            raise ValueError('bounds')
        if bounds['width'] <= 0 or bounds['height'] <= 0 or bounds['x'] + bounds['width'] > 1.000001 or bounds['y'] + bounds['height'] > 1.000001:
            raise ValueError('bounds')
        bbox = {key: round(float(value), 6) for key, value in bounds.items()}
        location = f"Página {segment['page']} · região OCR x={bbox['x']:.3f}, y={bbox['y']:.3f}, largura={bbox['width']:.3f}, altura={bbox['height']:.3f}"
        cleaned.append({'page': segment['page'], 'location': location, 'text': text, 'confidence': float(confidence), 'bbox': bbox})
    observed = {segment['page'] for segment in cleaned}
    if set(missing) != page_ids - observed:
        raise ValueError('missing coverage')
    text = '\n'.join(f"[{row['location']}] {row['text']}" for row in cleaned)
    if len(text.encode('utf-8')) > MAX_TEXT_BYTES:
        raise ValueError('text limit')
    scores = [row['confidence'] for row in cleaned]
    flags = (['no_text'] if not scores else []) + (['pages_without_text'] if missing else [])
    if scores and min(scores) < CONFIDENCE_THRESHOLD:
        flags.append('low_confidence')
    complete = bool(scores) and not flags
    return {'text': text, 'segments': cleaned, 'pages': pages, 'missing_pages': missing,
        'extraction_status': 'complete' if complete else 'inconclusive', 'engine': engine,
        'quality': {'assessment': 'review_required' if complete else 'inconclusive',
                    'minimum_confidence': min(scores) if scores else None,
                    'mean_confidence': sum(scores) / len(scores) if scores else None,
                    'threshold': CONFIDENCE_THRESHOLD, 'confidence_note': CONFIDENCE_NOTE, 'flags': flags},
        'limitations': LIMITATIONS}


def _tsv_segments(raw, page):
    if len(raw) > 300_000:
        raise ValueError('tsv size')
    lines = {}
    reader = csv.DictReader(io.StringIO(raw.decode('utf-8')), delimiter='\t', quoting=csv.QUOTE_NONE)
    expected = ['level', 'page_num', 'block_num', 'par_num', 'line_num', 'word_num', 'left', 'top', 'width', 'height', 'conf', 'text']
    if reader.fieldnames != expected:
        raise ValueError('tsv header')
    for word in reader:
        if set(word) != set(expected) or any(not isinstance(value, str) for value in word.values()):
            raise ValueError('tsv row')
        if word.get('level') != '5' or not word.get('text', '').strip():
            continue
        if len(lines) > MAX_SEGMENTS:
            raise ValueError('segments')
        score = float(word['conf']) / 100
        if not math.isfinite(score) or not 0 <= score <= 1:
            raise ValueError('confidence')
        x, y, width, height = (int(word[key]) for key in ('left', 'top', 'width', 'height'))
        if x < 0 or y < 0 or width <= 0 or height <= 0 or x + width > page['width'] or y + height > page['height']:
            raise ValueError('bounds')
        key = tuple(word[k] for k in ('block_num', 'par_num', 'line_num'))
        entry = lines.setdefault(key, {'words': [], 'scores': [], 'left': x, 'top': y, 'right': x + width, 'bottom': y + height})
        entry['words'].append(word['text']); entry['scores'].append(score)
        entry['left'] = min(entry['left'], x); entry['top'] = min(entry['top'], y)
        entry['right'] = max(entry['right'], x + width); entry['bottom'] = max(entry['bottom'], y + height)
    return [{'page': page['page'], 'text': ' '.join(line['words']), 'confidence': min(line['scores']),
             'bbox': {'x': line['left'] / page['width'], 'y': line['top'] / page['height'],
                      'width': (line['right'] - line['left']) / page['width'],
                      'height': (line['bottom'] - line['top']) / page['height']}}
            for line in lines.values()]


def extract(content, media_type):
    if media_type not in ('image/png', 'image/jpeg', 'application/pdf'):
        raise WorkflowError('OCR aceita somente PNG, JPEG e PDF sintéticos.')
    if not isinstance(content, bytes) or not 0 < len(content) <= MAX_BYTES:
        raise WorkflowError('OCR aceita arquivos entre 1 byte e 1 MiB.')
    if not configured():
        raise WorkflowError('OCR local não configurado. Instale Tesseract com idiomas por/eng e execute npm run setup:ocr no macOS.')
    started = time.monotonic()
    environment = {**os.environ, 'OMP_THREAD_LIMIT': '1'}
    def run(argv, **kwargs):
        remaining = TIMEOUT_SECONDS - (time.monotonic() - started)
        if remaining <= 0:
            raise subprocess.TimeoutExpired(argv, TIMEOUT_SECONDS)
        return subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                              timeout=remaining, check=False, env=environment, **kwargs)
    try:
        path = binary_path()
        binary_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        for language, expected in MODELS['models'].items():
            model = MODEL_DIRECTORY / f'{language}.traineddata'
            if model.stat().st_size != expected['bytes'] or hashlib.sha256(model.read_bytes()).hexdigest() != expected['sha256']:
                return _inconclusive('model_integrity_failed')
        recognizer = tesseract_path()
        version = run([recognizer, '--version'])
        if version.returncode != 0:
            return _inconclusive('reader_unavailable')
        engine = {'name': 'Tesseract', 'version': VERSION, 'runtime_version': version.stdout.decode('utf-8').splitlines()[0],
                  'os': os.uname().sysname + ' ' + os.uname().release, 'languages': ['por', 'eng'],
                  'rasterizer': 'PDFKit/ImageIO', 'binary_sha256': binary_hash, 'compute': 'CPU', 'page_segmentation_mode': 3, 'models': MODELS}
        with tempfile.TemporaryDirectory(prefix='elo-ocr-') as directory:
            # Directory mode 0700; generated PNGs mode 0600; always removed, including on timeout.
            result = run([str(path), media_type, directory], input=content)
            if result.returncode != 0 or len(result.stdout) > 4096:
                return _inconclusive('invalid_protected_or_limit_exceeded', engine)
            pages = json.loads(result.stdout)
            if not isinstance(pages, list) or not 1 <= len(pages) <= MAX_PAGES:
                return _inconclusive('invalid_reader_output', engine)
            segments, missing = [], []
            for number, page in enumerate(pages, 1):
                if not isinstance(page, dict) or page.get('page') != number or any(type(page.get(k)) is not int or not 1 <= page[k] <= 12000 for k in ('width', 'height')) or page['width'] * page['height'] > MAX_PIXELS:
                    return _inconclusive('invalid_reader_output', engine)
                image = Path(directory) / f'page-{number}.png'
                if not image.is_file() or image.is_symlink() or image.stat().st_size > 16 * 1024 * 1024:
                    return _inconclusive('raster_limit_exceeded', engine)
                recognized = run([recognizer, str(image), 'stdout', '--tessdata-dir', str(MODEL_DIRECTORY), '-l', 'por+eng', '--psm', '3', '-c', 'tessedit_create_tsv=1'])
                if recognized.returncode != 0:
                    return _inconclusive('recognizer_failed_or_language_unavailable', engine)
                rows = _tsv_segments(recognized.stdout, page)
                if not rows:
                    missing.append(number)
                segments.extend(rows)
                if len(segments) > MAX_SEGMENTS:
                    return _inconclusive('output_limit_exceeded', engine)
            return _validate({'segments': segments, 'pages': pages, 'missing_pages': missing, 'engine': engine})
    except subprocess.TimeoutExpired:
        return _inconclusive('processing_timeout', locals().get('engine'))
    except OSError:
        return _inconclusive('reader_unavailable', locals().get('engine'))
    except (ValueError, TypeError, KeyError, OverflowError, UnicodeDecodeError, IndexError):
        return _inconclusive('invalid_reader_output', locals().get('engine'))
