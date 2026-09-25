"""Private CSV search and owner-record PDF annex."""
import csv
from functools import lru_cache
import os
from pathlib import Path
import re

import pymupdf
import akash

CSV_PATH = Path(os.environ.get('OWNERS_CSV', Path(__file__).parent / 'data' / 'owners.csv'))


def unit_number(value):
    match = re.fullmatch(r'(?:[A-Za-z]\d+\s*-\s*)?([0-9]{4,5})', value.strip())
    return match.group(1) if match else None


@lru_cache(maxsize=1)
def records():
    with CSV_PATH.open(encoding='utf-8-sig', newline='') as source:
        reader = csv.DictReader(source)
        if not reader.fieldnames or 'Unit' not in reader.fieldnames:
            raise ValueError('The client CSV must contain a Unit column.')
        return [{k.strip(): (v or '').strip() for k, v in row.items() if k is not None}
                for row in reader]


def for_unit(unit):
    return [row for row in records() if unit_number(row.get('Unit', '')) == unit]


def search(query, page=1):
    tokens = query.casefold().split()
    groups = {}
    for index, row in enumerate(records()):
        unit = unit_number(row.get('Unit', ''))
        key = unit or 'record-%d' % index
        groups.setdefault(key, {'unit': unit, 'records': []})['records'].append(row)
    matches = []
    for group in groups.values():
        matching = [row for row in group['records']
                    if all(token in ' '.join(row.values()).casefold() for token in tokens)]
        if matching:
            group['matching_records'] = len(matching)
            matches.append(group)
    size = 12
    return {'results': matches[(page - 1) * size:page * size], 'total_units': len(matches),
            'page': page, 'pages': (len(matches) + size - 1) // size,
            'total_records': len(records())}


@lru_cache(maxsize=2048)
def available(unit):
    if not unit:
        return False
    try:
        u = akash.lookup(unit)
    except (SystemExit, Exception):
        return False
    u['doc'].close()
    return True


def wrap(value, width, size=9):
    lines = []
    for paragraph in str(value or '-').splitlines() or ['-']:
        line = ''
        for char in paragraph:
            if line and pymupdf.get_text_length(line + char, fontname='helv', fontsize=size) > width:
                lines.append(line)
                line = ''
            line += char
        lines.append(line)
    return lines


def append_records(brochure, unit, rows, add_diggaj_watermark=True, add_my_details=True):
    """Append every CSV field for every applicant of exactly the selected unit."""
    with pymupdf.open(stream=brochure, filetype='pdf') as doc:
        for index, row in enumerate(rows, 1):
            page = None
            y = 0
            for key, value in row.items():
                lines = wrap(value, 340)
                height = max(29, len(lines) * 13 + 13)
                if page is None or y + height > 755:
                    page = doc.new_page(width=595.28, height=841.89)
                    if add_diggaj_watermark:
                        akash.logo(page, 555, 44, 100)
                    akash.tx(page, 40, 42, 'OWNER RECORDS', 17, 'hebo', akash.NAVY)
                    akash.tx(page, 40, 62, 'UNIT %s  |  APPLICANT %d OF %d' % (unit, index, len(rows)), 9, 'helv', akash.GOLD)
                    akash.rule(page, 40, 80, 555, akash.GOLD_L)
                    if add_my_details:
                        akash.tx(page, 40, 101, 'Source: supplied booked-clients sheet. Records reproduced as provided.', 8, 'helv', akash.GREY)
                    y = 121
                akash.band(page, pymupdf.Rect(40, y, 555, y + height), akash.WASH)
                akash.tx(page, 49, y + 17, key, 8, 'hebo', akash.GREY)
                for line_index, line in enumerate(lines):
                    akash.tx(page, 201, y + 17 + line_index * 13, line, 9, 'helv', akash.INK)
                y += height + 4
        base_pages = 3 if add_diggaj_watermark else 2
        total = len(doc)
        for i, page in enumerate(doc):
            if i < base_pages:
                # Replace the original 3-page counter without touching contact details.
                rect = pymupdf.Rect(akash.W - 77, akash.H - 32, akash.W - 35, akash.H - 12)
                page.add_redact_annot(rect, fill=(1, 1, 1))
                page.apply_redactions(images=0, graphics=0)
                label = '%d / %d' % (i + 1, total)
                akash.tx(page, akash.W - akash.M - pymupdf.get_text_length(label, 'hebo', 7.5), akash.H - 22, label, 7.5, 'hebo', akash.NAVY)
            else:
                akash.rule(page, 40, 790, 555)
                if add_diggaj_watermark:
                    akash.tx(page, 40, 810, 'CONFIDENTIAL - CLIENT INFORMATION | DIGGAJ REALTY', 7, 'hebo', akash.GREY)
                akash.tx(page, 520, 810, '%d / %d' % (i + 1, total), 7, 'hebo', akash.NAVY)
        return doc.tobytes(deflate=True, garbage=4)
