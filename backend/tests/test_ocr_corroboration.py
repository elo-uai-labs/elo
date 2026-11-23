"""Conservative corroboration policy: no corpus ground truth enters runtime."""
from copy import deepcopy
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ocr


def row(texts, scores, page=1):
    return {'page': page, 'text': ' '.join(texts), 'confidence': min(scores),
            'words': [{'text': text, 'confidence': score} for text, score in zip(texts, scores)],
            'bbox': {'x': .1, 'y': .1, 'width': .8, 'height': .1}}


def result(primary, secondary):
    return ocr._validate({'pages': [{'page': 1, 'width': 100, 'height': 100}],
        'segments': primary, 'secondary_segments': secondary, 'missing_pages': [],
        'engine': {'name': 'Tesseract', 'version': ocr.VERSION, 'runtime_version': 'test', 'os': 'synthetic', 'languages': ['por', 'eng']}})


class CorroborationTest(unittest.TestCase):
    def test_separator_requires_exact_corroboration_and_preserves_scores(self):
        primary = [row(['CTR-701', '-', 'Fornecedor', 'FOR-701'], [.95, .52, .95, .95])]
        secondary = [row(['CTR-701', '-', 'Fornecedor', 'FOR-701'], [.95, .76, .95, .95])]
        observed = result(primary, secondary)
        self.assertEqual(observed['extraction_status'], 'complete')
        self.assertEqual(observed['quality']['assessment'], 'review_required')
        self.assertEqual(observed['quality']['minimum_confidence'], .52)
        self.assertEqual(observed['quality']['threshold'], .8)
        self.assertEqual(observed['quality']['flags'], ['low_confidence'])
        self.assertEqual(observed['quality']['secondary_segments'], secondary)
        self.assertEqual(observed['segments'][0]['words'], primary[0]['words'])
        self.assertIn('permanece incerto', observed['quality']['confidence_note'])
        self.assertEqual(result(primary, [])['extraction_status'], 'inconclusive')

    def test_secondary_high_confidence_exact_numeric_text_is_reviewable_not_verified(self):
        primary = [row(['Valor', '845,60'], [.95, .6])]
        secondary = [row(['Valor', '845,60'], [.95, .95])]
        observed = result(primary, secondary)
        self.assertEqual(observed['extraction_status'], 'complete')
        self.assertEqual(observed['quality']['minimum_confidence'], .6)
        self.assertIn('não comprova exatidão', observed['quality']['confidence_note'])
        for changed in ['845,80', '845.60', '-845,60']:
            with self.subTest(changed=changed):
                self.assertEqual(result(primary, [row(['Valor', changed], [.95, .95])])['extraction_status'], 'inconclusive')

    def test_financial_signs_ranges_and_cross_line_separator_remain_inconclusive(self):
        examples = [(['Saldo', '-', '120,00'], 1), (['CTR-701', '-', '12%'], 1),
                    (['CTR-701', '-', 'R$', '100'], 1), (['CTR-701', '-', 'USD', '100'], 1),
                    (['CTR-701', '-', 'CTR-702'], 1), (['Crédito', '-', 'Débito'], 1),
                    (['CTR-701', '+', 'Fornecedor'], 1), (['CTR-701', '-', 'Fornecedor'], 2)]
        for texts, weak in examples:
            with self.subTest(texts=texts, weak=weak):
                scores = [.95] * len(texts); scores[weak] = .6
                rows = [row(texts, scores)]
                self.assertEqual(result(rows, deepcopy(rows))['extraction_status'], 'inconclusive')
        rows = [row(['CTR-701'], [.95]), row(['-', 'Fornecedor'], [.6, .95])]
        self.assertEqual(result(rows, deepcopy(rows))['extraction_status'], 'inconclusive')

    def test_secondary_disagreement_missing_word_or_low_content_blocks(self):
        primary = [row(['CTR-701', '-', 'Fornecedor'], [.95, .6, .95])]
        for texts, scores in [(['CTR-701', '—', 'Fornecedor'], [.95]*3),
                              (['CTR-701', 'Fornecedor'], [.95]*2),
                              (['CTR-701', '-', 'Fornecedor'], [.7, .9, .95]),
                              (['CTR-702', '-', 'Fornecedor'], [.95]*3)]:
            self.assertEqual(result(primary, [row(texts, scores)])['extraction_status'], 'inconclusive')

    def test_word_scores_cannot_be_forged_or_have_invalid_types(self):
        primary = [row(['CTR-701', '-', 'Fornecedor'], [.95, .6, .95])]
        for value in [float('nan'), True, 1.1]:
            mutated = deepcopy(primary); mutated[0]['words'][1]['confidence'] = value
            with self.assertRaises(ValueError): result(mutated, primary)
        mutated = deepcopy(primary); mutated[0]['words'][1]['text'] = '+'
        with self.assertRaises(ValueError): result(mutated, primary)

    def test_second_pass_timeout_uses_remaining_budget_and_discards_output(self):
        with tempfile.TemporaryDirectory() as temp:
            executable = Path(temp) / 'raster'; executable.write_bytes(b'synthetic')
            directories, recognition_timeouts = [], []
            header = 'level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n'
            tsv = header + '5\t1\t1\t1\t1\t1\t1\t1\t5\t5\t60\tTeste\n'
            def run(argv, **kwargs):
                if '--version' in argv: return subprocess.CompletedProcess(argv, 0, b'tesseract test\n')
                if argv[0] == str(executable):
                    directory = Path(argv[2]); directories.append(directory)
                    (directory / 'page-1.png').write_bytes(b'synthetic')
                    return subprocess.CompletedProcess(argv, 0, b'[{"page":1,"width":10,"height":10}]')
                recognition_timeouts.append(kwargs['timeout'])
                if argv[argv.index('--psm') + 1] == '11':
                    raise subprocess.TimeoutExpired(argv, kwargs['timeout'])
                return subprocess.CompletedProcess(argv, 0, tsv.encode())
            with patch.object(ocr, 'configured', return_value=True), patch.object(ocr, 'binary_path', return_value=executable), patch.object(ocr.subprocess, 'run', side_effect=run), patch.object(ocr.time, 'monotonic', side_effect=[0, 1, 2, 10, 20]):
                observed = ocr.extract(b'synthetic', 'image/png')
            self.assertEqual(recognition_timeouts, [20, 10])
            self.assertEqual(observed['quality']['flags'], ['processing_timeout'])
            self.assertEqual(observed['segments'], [])
            self.assertTrue(all(not directory.exists() for directory in directories))
