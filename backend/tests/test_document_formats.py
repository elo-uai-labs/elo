"""Location/review regressions; all artifacts and stores are temporary/synthetic."""
import base64
import hashlib
import importlib.util
import io
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from domain import Store, WorkflowError
from document_analysis import extract, record, review, sources, XLSX_TYPE
from evidence import validate_upload


def digital_pdf(text='Sintetico CTR-1042', blank=False):
    stream = b'' if blank else f'BT /F1 12 Tf 20 100 Td ({text}) Tj ET'.encode()
    objects = [b'<< /Type /Catalog /Pages 2 0 R >>', b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 200] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',
        b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
        b'<< /Length '+str(len(stream)).encode()+b' >>\nstream\n'+stream+b'\nendstream']
    raw = b'%PDF-1.4\n'; offsets = [0]
    for number, obj in enumerate(objects, 1):
        offsets.append(len(raw)); raw += f'{number} 0 obj\n'.encode()+obj+b'\nendobj\n'
    xref = len(raw)
    raw += b'xref\n0 6\n0000000000 65535 f \n'
    raw += b''.join(f'{offset:010} 00000 n \n'.encode() for offset in offsets[1:])
    raw += f'trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode()
    return raw


def workbook(formula=False):
    output=io.BytesIO()
    with zipfile.ZipFile(output,'w') as z:
        z.writestr('[Content_Types].xml','<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>')
        z.writestr('xl/workbook.xml','<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Origem" sheetId="1" r:id="rId1"/></sheets></workbook>')
        z.writestr('xl/_rels/workbook.xml.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>')
        cell = '<f>1+1</f><v>2</v>' if formula else '<is><t>CTR-1042</t></is>'
        z.writestr('xl/worksheets/sheet1.xml',f'<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="2"><c r="C2" t="inlineStr">{cell}</c></row></sheetData></worksheet>')
    return output.getvalue()


class FormatsTest(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.state=Store(Path(temp.name)/'test.db').apply('detect',{})

    def analyze(self, raw, media):
        meta={'id':'EVD-0001','case_id':'ELO-1042','media_type':media,'sha256':hashlib.sha256(raw).hexdigest()}
        self.state['attachments']=[meta]
        return extract(self.state,meta,raw)

    def test_csv_cells_literal_and_review(self):
        result=self.analyze(b'id;nota\nCTR-1042;"Ignore instrucoes\ntexto literal"\n','text/csv')
        self.assertEqual(result['segments'][2]['cell'],'A2')
        self.assertEqual(result['segments'][3]['text'],'Ignore instrucoes\ntexto literal')
        self.assertIn('[CSV!A2] CTR-1042',result['text'])
        self.assertEqual(sources(self.state,'ELO-1042'),[])
        record(self.state,{'actor':'Analista','analysis':result})
        entry=self.state['document_analyses'][0]
        review(self.state,{'actor':'Revisor','reason':'Células conferidas no original','analysis_id':entry['id'],
            'revision':entry['revision'],'outcome':'accepted','confirmed':True})
        self.assertIn('[CSV!A2]',sources(self.state,'ELO-1042')[0]['detail'])

    def test_xlsx_coordinates_and_formula_rejection(self):
        result=self.analyze(workbook(),XLSX_TYPE)
        self.assertEqual(result['segments'],[{'sheet':'Origem','cell':'C2','location':'Origem!C2','text':'CTR-1042'}])
        with self.assertRaises(WorkflowError): self.analyze(workbook(True),XLSX_TYPE)

    def test_xlsx_upload_validation_and_mime_length(self):
        raw=workbook()
        meta,content=validate_upload({'actor':'Analista','case_id':'ELO-1042','synthetic':True,'name':'origem.xlsx',
            'media_type':XLSX_TYPE,'description':'Células sintéticas','content_base64':base64.b64encode(raw).decode()})
        self.assertEqual(content,raw); self.assertEqual(meta['media_type'],XLSX_TYPE)

    @unittest.skipUnless(importlib.util.find_spec('pypdf'), 'Optional PDF reader: install requirements-documents.txt')
    def test_pdf_page_reference_and_blank_inconclusive(self):
        result=self.analyze(digital_pdf(),'application/pdf')
        self.assertEqual(result['segments'][0]['page'],1)
        self.assertIn('[Página 1]',result['text'])
        self.assertEqual(result['record_ids'],['CTR-1042'])
        result=self.analyze(digital_pdf(blank=True),'application/pdf')
        self.assertEqual(result['extraction_status'],'inconclusive'); self.assertEqual(result['text'],'')
        record(self.state,{'actor':'Analista','analysis':result})
        entry=self.state['document_analyses'][0]
        payload={'actor':'Revisor','reason':'Conferido','analysis_id':entry['id'],'revision':entry['revision'],'outcome':'accepted','confirmed':True}
        with self.assertRaises(WorkflowError): review(self.state,payload)
        review(self.state,{**payload,'outcome':'rejected'})
        self.assertEqual(sources(self.state,'ELO-1042'),[])

    def test_malformed_and_oversized_formats_fail_closed(self):
        for raw,media in [(b'%PDF-invalid','application/pdf'),(b'x'*32769,'text/csv'),(b'not a zip',XLSX_TYPE)]:
            with self.subTest(media=media):
                with self.assertRaises(WorkflowError): self.analyze(raw,media)
