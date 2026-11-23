"""Bounded, immutable evidence bytes for the local synthetic workflow."""
import base64
import binascii
import hashlib
import re
from pathlib import PurePath

from domain import WorkflowError, required

MAX_FILE_BYTES = 1024 * 1024
MAX_TOTAL_BYTES = 20 * 1024 * 1024
MAX_FILES = 200
TYPES = {'text/plain': ('.txt',), 'application/pdf': ('.pdf',),
         'image/png': ('.png',), 'image/jpeg': ('.jpg', '.jpeg')}


def validate_upload(data):
    """Decode and sniff only. Never render, execute, OCR or send bytes to a model."""
    if data.get("synthetic") is not True:
        raise WorkflowError("Confirme que o arquivo contém exclusivamente dados sintéticos.")
    name = required(data, 'name', 120)
    media_type = required(data, 'media_type', 32)
    if '/' in name or '\\' in name or any(ord(character) < 32 or ord(character) == 127 for character in name):
        raise WorkflowError('O nome do arquivo não pode conter caminhos ou caracteres de controle.')
    if media_type not in TYPES or PurePath(name).suffix.lower() not in TYPES[media_type]:
        raise WorkflowError('Use arquivos TXT, PDF, PNG ou JPEG com extensão correspondente ao tipo informado.')
    encoded = data.get('content_base64')
    if not isinstance(encoded, str) or len(encoded) > ((MAX_FILE_BYTES + 2) // 3) * 4:
        raise WorkflowError('Cada arquivo aceita no máximo 1 MiB.', 413)
    try:
        content = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as error:
        raise WorkflowError('O conteúdo do arquivo não é um Base64 válido.') from error
    if not 0 < len(content) <= MAX_FILE_BYTES:
        raise WorkflowError('O arquivo precisa ter entre 1 byte e 1 MiB.', 413)
    if media_type == 'text/plain':
        try:
            text = content.decode('utf-8-sig')
        except UnicodeDecodeError as error:
            raise WorkflowError('O arquivo TXT precisa usar codificação UTF-8.') from error
        if any(ord(character) < 32 and character not in '\t\n\r' for character in text):
            raise WorkflowError('O arquivo TXT contém caracteres binários de controle.')
    elif media_type == 'application/pdf':
        if not re.match(rb'%PDF-(?:1\.[0-9]|2\.0)', content) or b'%%EOF' not in content[-1024:]:
            raise WorkflowError('O conteúdo não corresponde à assinatura esperada de um PDF.')
    elif media_type == 'image/png':
        if len(content) < 33 or not content.startswith(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR'):
            raise WorkflowError('O conteúdo não corresponde à assinatura esperada de um PNG.')
    elif not content.startswith(b'\xff\xd8\xff') or not content.endswith(b'\xff\xd9'):
        raise WorkflowError('O conteúdo não corresponde à assinatura esperada de um JPEG.')
    case_id = required(data, 'case_id', 64)
    action_id = data.get('action_id')
    if action_id is not None:
        action_id = required(data, 'action_id', 24)
    metadata = {'synthetic': True, 'case_id': case_id, 'name': name, 'media_type': media_type, 'size': len(content),
                'sha256': hashlib.sha256(content).hexdigest(), 'description': required(data, 'description'),
                'actor': required(data, 'actor', 80)}
    if action_id is not None:
        metadata['action_id'] = action_id
    return metadata, content


def download_filename(metadata):
    """Only the generated ID and known extension enter the response header."""
    return metadata['id'] + TYPES[metadata['media_type']][0]
