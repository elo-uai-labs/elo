"""Isolated, bounded PDF extraction worker. No OCR, actions or network execution."""
import io
import json
import resource
import sys


def main():
    resource.setrlimit(resource.RLIMIT_CPU, (3, 3))
    if sys.platform != 'darwin':
        resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
    from pypdf import PdfReader, Configuration
    for field in ('maximum_declared_stream_length', 'array_based_stream_maximum_output_length',
                  'jbig2_maximum_output_length', 'lzw_maximum_output_length',
                  'run_length_maximum_output_length', 'zlib_maximum_output_length',
                  'brotli_maximum_output_length', 'flate_maximum_row_length',
                  'image_maximum_buffer_size', 'stream_decoding_work_maximum_length'):
        setattr(Configuration, field, 2 * 1024 * 1024)
    raw = sys.stdin.buffer.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024:
        raise ValueError('size')
    reader = PdfReader(io.BytesIO(raw), strict=True)
    if reader.is_encrypted or not 1 <= len(reader.pages) <= 50:
        raise ValueError('encrypted or page limit')
    segments = []
    size = 0
    missing = []
    for number, page in enumerate(reader.pages, 1):
        text = page.extract_text()
        size += len(text.encode('utf-8'))
        if size > 32768:
            raise ValueError('text limit')
        if text.strip():
            segments.append({'page': number, 'location': f'Página {number}', 'text': text})
        else:
            missing.append(number)
    print(json.dumps({'segments': segments, 'missing_pages': missing}))


if __name__ == '__main__':
    try:
        main()
    except Exception:
        # No parser messages, document text, paths or sensitive bytes in error output.
        sys.exit(2)
