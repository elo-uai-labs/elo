"""Synthetic CSV/XLSX previews and atomic confirmation, using only temporary DBs."""
import base64
import io
from pathlib import Path
import sys
import tempfile
import unittest
from xml.sax.saxutils import escape
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from domain import Store, WorkflowError
from tabular_import import ImportFormatError, preview, read_xlsx


def payload(raw, table='employees', filename='base.csv', **options):
    return {'filename': filename, 'content_base64': base64.b64encode(raw).decode(), 'table': table, **options}


def xlsx(rows, extra=None):
    stream = io.BytesIO()
    xml_rows = []
    for number, cells in enumerate(rows, 1):
        xml_rows.append('<row r="%d">%s</row>' % (number, ''.join('<c r="%s%d" t="inlineStr"><is><t>%s</t></is></c>' % (chr(65 + index), number, escape(value)) for index, value in enumerate(cells))))
    entries = {
        'xl/workbook.xml': '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Pessoas" sheetId="1" r:id="rId1"/></sheets></workbook>',
        'xl/_rels/workbook.xml.rels': '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>',
        'xl/worksheets/sheet1.xml': '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>' + ''.join(xml_rows) + '</sheetData></worksheet>',
    }
    entries.update(extra or {})
    with zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, data in entries.items():
            archive.writestr(name, data)
    return stream.getvalue()


class TabularImportTest(unittest.TestCase):
    def test_csv_mapping_and_ignored_columns(self):
        raw = 'Código;Nome;Cargo;Contato;Observação\nEMP-CSV;Pessoa fictícia;Revisor;SYN-123;ignorar\n'.encode()
        request = payload(raw)
        initial = preview(request)
        self.assertFalse(initial['ready'])
        self.assertEqual(len(initial['errors']), 4)
        request['mapping'] = {'id': 'Código', 'name': 'Nome', 'role': 'Cargo', 'contact_code': 'Contato'}
        result = preview(request)
        self.assertTrue(result['ready'])
        self.assertEqual(result['dataset']['employees'][0]['name'], 'Pessoa fictícia')
        self.assertEqual(result['counts'], {'records': 1, 'valid': 1, 'errors': 0})
        self.assertIn('Observação', result['warnings'][0])

    def test_two_bases_reconcile_signals_and_persist(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'fixture.sqlite3'
            store = Store(path)
            store.apply('detect', {})
            for suffix, contact in [('YES', 'SYN-YES'), ('NO', 'SYN-DIFFERENT')]:
                tables = [
                    ('employees', 'id,name,role,contact_code\nEMP-%s,Fictício,Aprovador,SYN-%s\n' % (suffix, suffix)),
                    ('suppliers', 'id,name,contact_code\nFOR-%s,Fictício,%s\n' % (suffix, contact)),
                    ('contracts', 'id,supplier_id,approver_id,title\nCTR-%s,FOR-%s,EMP-%s,Contrato fictício\n' % (suffix, suffix, suffix)),
                ]
                for table, csv_text in tables:
                    result = preview(payload(csv_text.encode(), table), store.export_state()['dataset'])
                    self.assertTrue(result['ready'], result['errors'])
                    store.apply('import', {'actor': 'Teste sintético', 'synthetic': True, 'dataset': result['dataset']})
                outcome = store.apply('detect', {})
                self.assertEqual(outcome['audit'][-1]['details']['case_ids'], ['ELO-YES'] if suffix == 'YES' else [])
            self.assertEqual(Store(path).read(), store.read())

    def test_xlsx_literal_cells_and_physical_locations(self):
        raw = xlsx([['id', 'name', 'role', 'contact_code'], ['EMP-X', 'Fictício', 'Gestor', '']])
        result = preview(payload(raw, filename='base.xlsx'))
        self.assertTrue(result['ready'], result['errors'])
        self.assertEqual(result['sheets'], ['Pessoas'])
        self.assertEqual(result['rows'][0]['row'], 2)
        self.assertEqual(result['dataset']['employees'][0]['contact_code'], '')
        with self.assertRaises(ImportFormatError):
            read_xlsx(raw, 'Inexistente')

    def test_row_errors_and_no_partial_import(self):
        result = preview(payload(b'id,name,role,contact_code\nEMP-X,Ficticio,A,SYN\nEMP-X,Ficticio,A,SYN\nERR,,A,SYN\n'))
        self.assertFalse(result['ready'])
        self.assertEqual(result['dataset']['employees'], [])
        self.assertEqual({e['row'] for e in result['errors']}, {3, 4})
        self.assertEqual(result['counts']['records'], 3)
        self.assertEqual(result['counts']['valid'], 1)

    def test_unknown_references_and_existing_ids(self):
        result = preview(payload(b'id,supplier_id,approver_id,title\nCTR-X,FOR-X,EMP-X,Ficticio\n', 'contracts'))
        self.assertEqual(len(result['errors']), 2)
        result = preview(payload(b'id,name,role,contact_code\nEMP-X,Ficticio,A,SYN\n'), {'employees': [{'id': 'EMP-X'}]})
        self.assertFalse(result['ready'])

    def test_confirm_revalidates_stale_preview_atomically(self):
        with tempfile.TemporaryDirectory() as folder:
            store = Store(Path(folder) / 'test.sqlite3')
            result = preview(payload(b'id,name,role,contact_code\nEMP-X,Ficticio,A,SYN\n'))
            body = {'actor': 'Teste', 'synthetic': True, 'dataset': result['dataset']}
            store.apply('import', body)
            before = store.read()
            with self.assertRaises(WorkflowError):
                store.apply('import', body)
            self.assertEqual(before, store.read())

    def test_rejects_malformed_headers_encoding_and_mapping(self):
        cases = [payload(b'id,id\nA,B\n'), payload(b'id,\nA,B\n'), payload(b'\xff'), payload(b'x\n1\n', mapping={'id': 'missing'}), payload(b'id,name\nA,B\n', mapping={'id': 'id', 'name': 'id'})]
        for case in cases:
            with self.subTest(case=case), self.assertRaises(ImportFormatError):
                preview(case)

    def test_rejects_oversized_or_malicious_xlsx(self):
        for extra in [
            {'xl/vbaProject.bin': 'macro'},
            {'xl/_rels/evil.rels': '<Relationships><Relationship TargetMode="External" Target="https://example.invalid"/></Relationships>'},
            {'xl/worksheets/sheet1.xml': '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="1"><c r="A1"><f>1+1</f><v>2</v></c></row></sheetData></worksheet>'},
            {'xl/sharedStrings.xml': '<!DOCTYPE x [<!ENTITY y "bad">]><x/>'},
            {'xl/sharedStrings.xml': 'x' * (4 * 1024 * 1024 + 1)},
        ]:
            with self.subTest(extra=list(extra)), self.assertRaises(ImportFormatError):
                preview(payload(xlsx([['id']], extra), filename='base.xlsx'))
        with self.assertRaises(ImportFormatError):
            preview(payload(b'x' * (256 * 1024 + 1)))

    def test_row_limit_and_semicolon_csv_quotes(self):
        with self.assertRaises(ImportFormatError):
            preview(payload(b'id,name,role,contact_code\n' + b'EMP-X,Ficticio,A,SYN\n' * 501))
        result = preview(payload(b'id;name;role;contact_code\nEMP-X;"Pessoa; ficticia";A;SYN\n'))
        self.assertTrue(result['ready'])
        self.assertEqual(result['dataset']['employees'][0]['name'], 'Pessoa; ficticia')


if __name__ == '__main__':
    unittest.main()
