"""Local OCR boundary and measured synthetic quality; no application database."""
import base64
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ocr
from domain import WorkflowError
from ocr_fixtures import build_fixtures, EXPECTED_TEXT


def raw_result(confidence=0.95):
    return {'pages': [{'page': 1, 'width': 1200, 'height': 600}], 'missing_pages': [],
        'engine': {'name': 'Tesseract', 'version': ocr.VERSION, 'runtime_version': 'tesseract test', 'os': 'synthetic', 'languages': ['por', 'eng']},
        'segments': [{'page': 1, 'text': 'CTR-1042', 'confidence': confidence,
            'bbox': {'x': 0.1, 'y': 0.2, 'width': 0.3, 'height': 0.1}}]}


def distance(a, b):
    previous = list(range(len(b) + 1))
    for i, left in enumerate(a, 1):
        current = [i]
        for j, right in enumerate(b, 1):
            current.append(min(current[-1] + 1, previous[j] + 1, previous[j - 1] + (left != right)))
        previous = current
    return previous[-1]


class OCRBoundaryTest(unittest.TestCase):
    def test_quality_is_derived_and_low_confidence_is_inconclusive(self):
        response = ocr._validate(raw_result())
        self.assertEqual(response['extraction_status'], 'complete')
        self.assertIn('não probabilidade', response['quality']['confidence_note'])
        self.assertIn('x=0.100', response['text'])
        low = raw_result(.79); low['extraction_status'] = 'complete'; low['quality'] = {'assessment': 'perfect'}
        response = ocr._validate(low)
        self.assertEqual(response['extraction_status'], 'inconclusive')
        self.assertEqual(response['quality']['flags'], ['low_confidence'])

    def test_malformed_output_and_page_coverage_fail(self):
        for mutate in [lambda r: r['segments'][0].update(confidence=float('nan')),
                       lambda r: r['segments'][0].update(confidence=True),
                       lambda r: r['segments'][0]['bbox'].update(x=.9),
                       lambda r: r['segments'][0].update(page=2),
                       lambda r: r.update(missing_pages=[1]),
                       lambda r: r['segments'][0].update(text='\x00'),
                       lambda r: r['engine'].update(name='unexpected')]:
            value = raw_result(); mutate(value)
            with self.assertRaises(ValueError): ocr._validate(value)
        value = raw_result(); value['pages'].append({'page': 2, 'width': 1200, 'height': 600}); value['missing_pages'] = [2]
        self.assertEqual(ocr._validate(value)['extraction_status'], 'inconclusive')

    def test_tsv_structure_and_minimum_word_score(self):
        header = 'level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n'
        page = {'page': 1, 'width': 1200, 'height': 600}
        data = header + '5\t1\t1\t1\t1\t1\t10\t20\t100\t20\t95\tCTR-1042\n5\t1\t1\t1\t1\t2\t120\t20\t80\t20\t79\tFICTICIO\n'
        segments = ocr._tsv_segments(data.encode(), page)
        self.assertEqual(segments[0]['text'], 'CTR-1042 FICTICIO'); self.assertEqual(segments[0]['confidence'], .79)
        for malformed in [b'level\ttext\n5\n', (header + '5\t1\n').encode(), (data + '5\t1\t1\t1\t1\t3\t10\t20\t100\t20\tnan\tbad\n').encode()]:
            with self.assertRaises(ValueError): ocr._tsv_segments(malformed, page)

    def test_minimal_path_uses_homebrew_without_overriding_explicit_choice(self):
        with patch.dict(ocr.os.environ, {'PATH': ''}, clear=True), patch.object(ocr.shutil, 'which', return_value=None), patch.object(ocr, '_executable', side_effect=lambda path: path == '/opt/homebrew/bin/tesseract'):
            self.assertEqual(ocr.tesseract_path(), '/opt/homebrew/bin/tesseract')
        with patch.dict(ocr.os.environ, {'PATH': '', 'ELO_TESSERACT_BIN': '/invalid/explicit'}, clear=True), patch.object(ocr.shutil, 'which') as discover:
            self.assertEqual(ocr.tesseract_path(), '/invalid/explicit')
            discover.assert_not_called()

    def test_unavailable_and_size_bounds(self):
        with patch.object(ocr, 'configured', return_value=False):
            with self.assertRaises(WorkflowError): ocr.extract(b'png', 'image/png')
        for content, media in [(b'x' * (ocr.MAX_BYTES + 1), 'image/png'), (b'', 'image/png'), (b'text', 'text/plain')]:
            with self.assertRaises(WorkflowError): ocr.extract(content, media)

    def test_timeout_discards_output_and_removes_private_temporary_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            executable = Path(temp) / 'raster'; executable.write_bytes(b'synthetic')
            directories = []
            def run(argv, **kwargs):
                if '--version' in argv: return subprocess.CompletedProcess(argv, 0, b'tesseract test\n')
                if str(executable) == argv[0]:
                    directory = Path(argv[2]); directories.append(directory)
                    self.assertEqual(directory.stat().st_mode & 0o777, 0o700)
                    (directory / 'page-1.png').write_bytes(b'fixture')
                    return subprocess.CompletedProcess(argv, 0, b'[{"page":1,"width":10,"height":10}]')
                raise subprocess.TimeoutExpired(argv, 30)
            with patch.object(ocr, 'configured', return_value=True), patch.object(ocr, 'binary_path', return_value=executable), patch.object(ocr, 'MODELS', {'models': {}}), patch.object(ocr.subprocess, 'run', side_effect=run):
                result = ocr.extract(b'png', 'image/png')
            self.assertEqual(result['quality']['flags'], ['processing_timeout'])
            self.assertEqual(result['segments'], [])
            self.assertTrue(directories); self.assertTrue(all(not directory.exists() for directory in directories))


@unittest.skipUnless(sys.platform == 'darwin' and ocr.configured(), 'Set up local OCR with npm run setup:ocr')
class OCRRealEngineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixtures = {name: base64.b64decode(raw) for name, raw in build_fixtures().items()}

    def test_quality_on_clear_degraded_and_blank_fixtures(self):
        measurements = []
        for name, media, complete in [('png', 'image/png', True), ('jpeg', 'image/jpeg', True), ('pdf', 'application/pdf', True),
                                      ('blank', 'image/png', False), ('degraded', 'image/png', False), ('portuguese', 'image/png', True)]:
            with self.subTest(fixture=name):
                started = time.monotonic(); result = ocr.extract(self.fixtures[name], media); elapsed = time.monotonic() - started
                actual = '\n'.join(segment['text'] for segment in result['segments'])
                expected = 'AÇÃO DE REVISÃO\nCONTRATO SINTÉTICO\nFORNECEDOR FICTÍCIO' if name == 'portuguese' else EXPECTED_TEXT
                errors = distance(expected, actual)
                self.assertEqual(result['extraction_status'], 'complete' if complete else 'inconclusive')
                if complete:
                    self.assertEqual(actual, expected)
                    self.assertTrue(all(segment['page'] == 1 and 0 <= segment['bbox']['x'] <= 1 for segment in result['segments']))
                else: self.assertEqual(actual, '')
                self.assertLess(elapsed, ocr.TIMEOUT_SECONDS)
                measurements.append({'fixture': name, 'input_sha256': hashlib.sha256(self.fixtures[name]).hexdigest(),
                    'expected_text': expected if name != 'blank' else '', 'actual_text': actual,
                    'character_errors': errors if name != 'blank' else len(actual), 'reference_characters': len(expected) if name != 'blank' else 0,
                    'cer': errors / len(expected) if name != 'blank' else None, 'extraction_status': result['extraction_status'],
                    'quality': result['quality'], 'elapsed_seconds': elapsed, 'engine': result['engine']})
        output = Path(__file__).resolve().parents[2] / 'output' / 'validation'; output.mkdir(parents=True, exist_ok=True)
        (output / 'ocr-quality.json').write_text(json.dumps({'scope': 'Six synthetic fixtures; not representative of real documents or production accuracy.',
            'ground_truth': EXPECTED_TEXT, 'method': 'Character-level Levenshtein distance, including spaces and line breaks; confidence reported separately.',
            'measurements': measurements}, ensure_ascii=False, indent=2))

    def test_exif_orientation_and_source_location(self):
        original = ocr.extract(self.fixtures['jpeg'], 'image/jpeg')
        rotated = ocr.extract(self.fixtures['jpeg_exif'], 'image/jpeg')
        self.assertEqual(rotated['extraction_status'], 'complete')
        self.assertEqual('\n'.join(segment['text'] for segment in rotated['segments']), EXPECTED_TEXT)
        self.assertEqual(rotated['pages'], original['pages'])
        for before, after in zip(original['segments'], rotated['segments']):
            for coordinate in ('x', 'y', 'width', 'height'):
                self.assertAlmostEqual(before['bbox'][coordinate], after['bbox'][coordinate], delta=.01)

    def test_page_pixel_and_invalid_file_limits(self):
        for fixture, media in [('oversized', 'image/png'), ('pdf_six_pages', 'application/pdf')]:
            result = ocr.extract(self.fixtures[fixture], media)
            self.assertEqual(result['extraction_status'], 'inconclusive'); self.assertEqual(result['segments'], [])
            self.assertIn('invalid_protected_or_limit_exceeded', result['quality']['flags'])
        self.assertEqual(ocr.extract(b'not an image', 'image/png')['extraction_status'], 'inconclusive')
