from pathlib import Path
import textwrap

INPUT = Path('docs/project_summary.md')
OUTPUT = Path('docs/project_summary.pdf')
PAGE_WIDTH = 612
PAGE_HEIGHT = 792
LEFT_MARGIN = 54
TOP_MARGIN = 60
FONT_SIZE = 12
LEADING = 15
MAX_TEXT_WIDTH_CHARS = 92


def escape_pdf_text(text: str) -> str:
    return text.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')


def parse_pages(markdown_text: str):
    raw_pages = [p.strip('\n') for p in markdown_text.split('\n---PAGE BREAK---\n')]
    pages = []
    for raw in raw_pages:
        lines = []
        for raw_line in raw.splitlines():
            line = raw_line.strip()
            if not line:
                lines.append('')
                continue
            if line.startswith('# '):
                lines.append(line[2:].upper())
                lines.append('')
                continue
            if line.startswith('## '):
                lines.append(line[3:])
                lines.append('')
                continue
            if line.startswith('### '):
                lines.append(line[4:])
                continue
            if line.startswith('- '):
                lines.extend(textwrap.wrap('• ' + line[2:], width=MAX_TEXT_WIDTH_CHARS) or [''])
                continue
            if len(line) > 3 and line[0].isdigit() and line[1:3] == '. ':
                lines.extend(textwrap.wrap(line, width=MAX_TEXT_WIDTH_CHARS) or [''])
                continue
            lines.extend(textwrap.wrap(line, width=MAX_TEXT_WIDTH_CHARS) or [''])
        pages.append(lines)
    return pages


def build_content_stream(lines):
    y = PAGE_HEIGHT - TOP_MARGIN
    commands = ['BT', f'/F1 {FONT_SIZE} Tf', f'{LEFT_MARGIN} {y} Td']
    first = True
    for line in lines:
        if not first:
            commands.append(f'0 -{LEADING} Td')
        first = False
        commands.append(f'({escape_pdf_text(line)}) Tj')
    commands.append('ET')
    return '\n'.join(commands).encode('latin-1', errors='replace')


def generate_pdf(pages_lines):
    objects = []

    def add_object(data: bytes) -> int:
        objects.append(data)
        return len(objects)

    font_obj = add_object(b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>')

    content_obj_ids = []
    for lines in pages_lines:
        stream = build_content_stream(lines)
        content = b'<< /Length ' + str(len(stream)).encode() + b' >>\nstream\n' + stream + b'\nendstream'
        content_obj_ids.append(add_object(content))

    pages_obj_id = len(objects) + 1
    page_obj_ids = []

    for content_id in content_obj_ids:
        page = (
            f'<< /Type /Page /Parent {pages_obj_id} 0 R '
            f'/MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] '
            f'/Resources << /Font << /F1 {font_obj} 0 R >> >> '
            f'/Contents {content_id} 0 R >>'
        ).encode('latin-1')
        page_obj_ids.append(add_object(page))

    kids = ' '.join(f'{pid} 0 R' for pid in page_obj_ids)
    pages_obj = f'<< /Type /Pages /Kids [ {kids} ] /Count {len(page_obj_ids)} >>'.encode('latin-1')
    add_object(pages_obj)

    catalog_obj = add_object(f'<< /Type /Catalog /Pages {pages_obj_id} 0 R >>'.encode('latin-1'))

    pdf = bytearray(b'%PDF-1.4\n')
    offsets = [0]
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f'{i} 0 obj\n'.encode('latin-1'))
        pdf.extend(obj)
        pdf.extend(b'\nendobj\n')

    xref_start = len(pdf)
    pdf.extend(f'xref\n0 {len(objects) + 1}\n'.encode('latin-1'))
    pdf.extend(b'0000000000 65535 f \n')
    for i in range(1, len(objects) + 1):
        pdf.extend(f'{offsets[i]:010d} 00000 n \n'.encode('latin-1'))

    pdf.extend(
        f'trailer\n<< /Size {len(objects) + 1} /Root {catalog_obj} 0 R >>\nstartxref\n{xref_start}\n%%EOF\n'.encode('latin-1')
    )

    OUTPUT.write_bytes(pdf)


def main():
    pages = parse_pages(INPUT.read_text(encoding='utf-8'))
    if len(pages) != 3:
        raise ValueError(f'Expected exactly 3 pages, got {len(pages)}')
    generate_pdf(pages)


if __name__ == '__main__':
    main()
