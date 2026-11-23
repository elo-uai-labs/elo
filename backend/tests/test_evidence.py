import base64
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from domain import WorkflowError
from evidence import MAX_FILE_BYTES, validate_upload


class EvidenceValidationTest(unittest.TestCase):
    def payload(self, content=b'Evidencia sintetica\n', name='ata.txt', media_type='text/plain'):
        return {'synthetic': True, 'actor': 'Analista', 'case_id': 'ELO-1042', 'name': name, 'media_type': media_type,
                'description': 'Registro sintético', 'content_base64': base64.b64encode(content).decode()}

    def test_supported_signatures_and_hash(self):
        for content, name, media_type in (
            (b'Ata sintetica\n', 'ata.txt', 'text/plain'),
            (b'%PDF-1.7\nsynthetic\n%%EOF', 'ata.pdf', 'application/pdf'),
            (b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR' + bytes(17), 'ata.png', 'image/png'),
            (b'\xff\xd8\xffsynthetic\xff\xd9', 'ata.jpeg', 'image/jpeg'),
        ):
            metadata, result = validate_upload(self.payload(content, name, media_type))
            self.assertEqual(result, content)
            self.assertEqual(metadata['size'], len(content))
            self.assertEqual(len(metadata['sha256']), 64)

    def test_invalid_type_path_signature_encoding_size_rejected(self):
        for payload in (
            self.payload(name='../ata.txt'), self.payload(name='ata.txt\r\nX-Header: x'),
            self.payload(b'<html></html>', 'ata.pdf', 'application/pdf'),
            self.payload(b'not png', 'ata.png', 'image/png'),
            self.payload(b'not jpeg', 'ata.jpg', 'image/jpeg'),
            self.payload(b'\x00binary'), self.payload(b'\xff'), self.payload(b''),
            self.payload(b'x' * (MAX_FILE_BYTES + 1)), self.payload(name='ata.html'),
            {**self.payload(), 'content_base64': '%%%invalid'},
            {**self.payload(), 'synthetic': False},
        ):
            with self.assertRaises(WorkflowError):
                validate_upload(payload)


if __name__ == '__main__':
    unittest.main()
