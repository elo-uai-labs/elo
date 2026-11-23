"""Bounded, read-only CSV/XLSX preview; confirmation uses the existing atomic import.

Only literal spreadsheet cells are accepted. Formulas, external relationships,
macros and ambiguous CSV headers are rejected, never evaluated or fetched.
"""
import base64
import binascii
import csv
import io
import posixpath
import re
import zipfile
import xml.etree.ElementTree as ET

FIELDS = {
    'employees': ('id', 'name', 'role', 'contact_code'),
    'suppliers': ('id', 'name', 'contact_code'),
    'contracts': ('id', 'supplier_id', 'approver_id', 'title'),
}
PREFIXES = {'employees': 'EMP-', 'suppliers': 'FOR-', 'contracts': 'CTR-'}
MAX_FILE = 256 * 1024
MAX_XML = 4 * 1024 * 1024
NS = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
REL = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'


class ImportFormatError(ValueError):
    pass


def _xml(raw):
    if b'\x00' in raw or b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():
        raise ImportFormatError('Declarações XML externas ou entidades não são aceitas.')
    try:
        return ET.fromstring(raw)
    except ET.ParseError as exc:
        raise ImportFormatError('XML da planilha inválido.') from exc


def read_xlsx(raw, sheet=None):
    """Return sheet names, selected sheet and (physical row number, cells) pairs."""
    try:
        archive = zipfile.ZipFile(io.BytesIO(raw))
    except (zipfile.BadZipFile, OSError) as exc:
        raise ImportFormatError('Arquivo XLSX inválido.') from exc
    with archive:
        entries = archive.infolist()
        names = [entry.filename for entry in entries]
        if len(entries) > 100 or len(set(names)) != len(names) or sum(e.file_size for e in entries) > MAX_XML:
            raise ImportFormatError('Planilha excede os limites locais de expansão ou contém entradas duplicadas.')
        if any(e.flag_bits & 1 or e.file_size > MAX_XML for e in entries):
            raise ImportFormatError('Planilha criptografada ou excessiva não é aceita.')
        if any('vbaproject' in name.lower() or 'externallinks/' in name.lower() for name in names):
            raise ImportFormatError('Macros e vínculos externos não são aceitos.')
        def read(name):
            try:
                return archive.read(name)
            except (KeyError, zipfile.BadZipFile, RuntimeError, NotImplementedError) as exc:
                raise ImportFormatError('Estrutura XLSX inválida ou não suportada.') from exc
        if '[Content_Types].xml' in names and b'macroenabled' in read('[Content_Types].xml').lower():
            raise ImportFormatError('Planilhas habilitadas para macros não são aceitas.')
        for name in names:
            if name.endswith('.rels'):
                root = _xml(read(name))
                if any(rel.get('TargetMode', '').lower() == 'external' for rel in root):
                    raise ImportFormatError('Vínculos externos não são aceitos.')
        workbook = _xml(read('xl/workbook.xml'))
        relationships = _xml(read('xl/_rels/workbook.xml.rels'))
        targets = {r.get('Id'): r.get('Target', '') for r in relationships}
        sheets = workbook.findall('s:sheets/s:sheet', NS)
        sheet_names = [s.get('name', '') for s in sheets]
        if not sheets or len(set(sheet_names)) != len(sheet_names):
            raise ImportFormatError('A planilha precisa ter abas identificáveis.')
        if sheet is None:
            sheet = sheet_names[0]
        if sheet not in sheet_names:
            raise ImportFormatError('Aba selecionada não existe.')
        selected = sheets[sheet_names.index(sheet)]
        target = targets.get(selected.get('{' + REL + '}id'), '')
        path = posixpath.normpath(target.lstrip('/') if target.startswith('/') else 'xl/' + target)
        if not path.startswith('xl/worksheets/') or not path.endswith('.xml'):
            raise ImportFormatError('Destino da aba inválido.')
        strings = []
        if 'xl/sharedStrings.xml' in names:
            strings = [''.join(t.text or '' for t in node.findall('.//s:t', NS)) for node in _xml(read('xl/sharedStrings.xml')).findall('s:si', NS)]
        root = _xml(read(path))
        if root.findall('.//s:f', NS):
            raise ImportFormatError('Fórmulas não são aceitas. Exporte uma cópia contendo somente valores.')
        rows = []
        row_numbers = set()
        for index, row in enumerate(root.findall('s:sheetData/s:row', NS), 1):
            if len(rows) >= 501:
                raise ImportFormatError('Cada tabela aceita até 500 registros, além do cabeçalho.')
            try:
                row_number = int(row.get('r', str(index)))
            except ValueError as exc:
                raise ImportFormatError('Número de linha inválido.') from exc
            if not 1 <= row_number <= 1048576 or row_number in row_numbers:
                raise ImportFormatError('Número de linha inválido ou duplicado.')
            row_numbers.add(row_number)
            values = {}
            for cell in row.findall('s:c', NS):
                match = re.fullmatch(r'([A-Z]{1,3})([1-9][0-9]*)', cell.get('r', ''))
                if not match or int(match.group(2)) != row_number:
                    raise ImportFormatError('Coordenada de célula inválida.')
                column = 0
                for letter in match.group(1):
                    column = column * 26 + ord(letter) - 64
                if column > 32 or column in values:
                    raise ImportFormatError('Máximo de 32 colunas; células duplicadas não são aceitas.')
                kind = cell.get('t', 'n')
                value = cell.findtext('s:v', '', NS)
                if kind == 's':
                    if not value.isdigit() or int(value) >= len(strings):
                        raise ImportFormatError('Índice de texto da célula inválido.')
                    value = strings[int(value)]
                elif kind == 'inlineStr':
                    value = ''.join(t.text or '' for t in cell.findall('s:is//s:t', NS))
                elif kind not in ('n', 'str', 'b'):
                    raise ImportFormatError('Célula com erro ou tipo não suportado.')
                values[column] = value
            cells = [values.get(i, '') for i in range(1, max(values, default=0) + 1)]
            if any(cells):
                rows.append((row_number, cells))
        return sheet_names, sheet, rows


def _csv(raw):
    try:
        content = raw.decode('utf-8-sig')
    except UnicodeDecodeError as exc:
        raise ImportFormatError('CSV precisa usar UTF-8.') from exc
    if '\x00' in content:
        raise ImportFormatError('CSV contém byte nulo.')
    # Delimiter is selected from the first physical header line, not guessed from data.
    header = content.splitlines()[0] if content.splitlines() else ''
    delimiter = ';' if header.count(';') > header.count(',') else ','
    reader = csv.reader(io.StringIO(content, newline=''), delimiter=delimiter, strict=True)
    rows = []
    try:
        for cells in reader:
            if len(cells) > 32 or len(rows) >= 501:
                raise ImportFormatError('Máximo de 32 colunas e 500 registros por tabela.')
            if any(cells):
                rows.append((reader.line_num, cells))
    except csv.Error as exc:
        raise ImportFormatError('CSV malformado.') from exc
    return rows


def preview(payload, existing_dataset=None):
    """No writes. Return schema, reconciled row errors and an all-or-nothing dataset."""
    if not isinstance(payload, dict) or not isinstance(payload.get('table'), str) or payload['table'] not in FIELDS:
        raise ImportFormatError('Selecione employees, suppliers ou contracts.')
    table = payload['table']
    filename = payload.get('filename')
    encoded = payload.get('content_base64')
    if not isinstance(filename, str) or len(filename) > 180 or not isinstance(encoded, str) or len(encoded) > (MAX_FILE + 2) // 3 * 4:
        raise ImportFormatError('Informe arquivo de até 256 KiB.')
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ImportFormatError('Conteúdo base64 inválido.') from exc
    if not raw or len(raw) > MAX_FILE:
        raise ImportFormatError('Informe arquivo não vazio de até 256 KiB.')
    extension = filename.rsplit('.', 1)[-1].lower()
    if extension == 'csv':
        sheets, sheet, rows = [], None, _csv(raw)
    elif extension == 'xlsx':
        sheets, sheet, rows = read_xlsx(raw, payload.get('sheet'))
    else:
        raise ImportFormatError('Formatos aceitos: CSV UTF-8 e XLSX sem fórmulas.')
    if not rows:
        raise ImportFormatError('Arquivo sem cabeçalho.')
    columns = [v.strip() for v in rows[0][1]]
    if not columns or any(not v or len(v) > 160 for v in columns) or len(set(columns)) != len(columns):
        raise ImportFormatError('Cabeçalhos precisam ser únicos, preenchidos e ter até 160 caracteres.')
    mapping = payload.get('mapping', {field: field for field in FIELDS[table] if field in columns})
    if not isinstance(mapping, dict) or set(mapping) - set(FIELDS[table]) or any(not isinstance(v, str) or v not in columns for v in mapping.values()):
        raise ImportFormatError('Mapeamento inválido. Use campo de destino e cabeçalho de origem.')
    if len(set(mapping.values())) != len(mapping):
        raise ImportFormatError('Cada coluna só pode mapear um campo.')
    errors, warnings, result_rows = [], [], []
    missing = set(FIELDS[table]) - set(mapping)
    for field in sorted(missing):
        errors.append({'row': rows[0][0], 'field': field, 'message': 'Mapeie este campo obrigatório.'})
    ignored = [name for name in columns if name not in mapping.values()]
    if ignored:
        warnings.append('Colunas ignoradas: ' + ', '.join(ignored))
    existing = existing_dataset or {name: [] for name in FIELDS}
    ids = {r['id'] for r in existing.get(table, [])}
    seen = set()
    for row_number, cells in rows[1:]:
        item = {}
        if len(cells) > len(columns):
            errors.append({'row': row_number, 'field': '', 'message': 'Linha tem mais células que o cabeçalho.'})
        for field, source in mapping.items():
            index = columns.index(source)
            value = (cells[index] if index < len(cells) else '').strip()
            item[field] = value
            if (not value and field != 'contact_code') or len(value) > 160 or any(ord(c) < 32 for c in value):
                errors.append({'row': row_number, 'field': field, 'message': 'Valor obrigatório (exceto contact_code), até 160 caracteres e sem controles.'})
        identifier = item.get('id', '')
        if 'id' in mapping:
            if not re.fullmatch(PREFIXES[table] + r'[A-Za-z0-9_-]{1,48}', identifier):
                errors.append({'row': row_number, 'field': 'id', 'message': 'ID inválido para a tabela selecionada.'})
            elif identifier in ids or identifier in seen:
                errors.append({'row': row_number, 'field': 'id', 'message': 'ID já existente ou duplicado no arquivo.'})
            seen.add(identifier)
        if table == 'contracts':
            for field, reference in [('approver_id', 'employees'), ('supplier_id', 'suppliers')]:
                if field in mapping and item[field] not in {r['id'] for r in existing.get(reference, [])}:
                    errors.append({'row': row_number, 'field': field, 'message': 'Referência inexistente; importe empregados e fornecedores primeiro.'})
        result_rows.append({'row': row_number, 'values': item})
    if not result_rows:
        errors.append({'row': rows[0][0], 'field': '', 'message': 'Arquivo precisa conter registros.'})
    if len(existing.get(table, [])) + len(result_rows) > 2000:
        errors.append({'row': 0, 'field': '', 'message': 'Limite local de 2.000 registros por tabela.'})
    invalid_rows = {error['row'] for error in errors}
    dataset = {name: [] for name in FIELDS}
    if not errors:
        dataset[table] = [row['values'] for row in result_rows]
    return {'format': extension, 'sheets': sheets, 'sheet': sheet, 'table': table,
            'columns': columns, 'mapping': mapping, 'rows': result_rows,
            'errors': errors, 'warnings': warnings, 'ready': not errors, 'dataset': dataset,
            'counts': {'records': len(result_rows), 'valid': 0 if missing else sum(r['row'] not in invalid_rows for r in result_rows), 'errors': len(errors)}}
