import sys
from pathlib import Path
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pymupdf
import app
import owners


class AppTests(unittest.TestCase):
    def setUp(self):
        self.client = app.app.test_client()

    def test_home_and_private_source(self):
        self.assertEqual(self.client.get('/').status_code, 200)
        self.assertEqual(self.client.get('/health').status_code, 200)
        self.assertEqual(self.client.get('/data/owners.csv').status_code, 404)

    def test_search_each_field_and_coapplicants(self):
        row = owners.for_unit('4102')[0]
        for field in ('Applicant Name', 'Email Address', 'Mobile Number', 'Unit'):
            result = self.client.post('/api/owners/search', json={'query': row[field]}).get_json()
            match = next(group for group in result['results'] if group['unit'] == '4102')
            self.assertEqual(len(match['records']), len(owners.for_unit('4102')))
            self.assertTrue(match['can_combine'])
            self.assertEqual(len(match['records'][0]), 16)

    def test_pagination_and_no_results(self):
        first = self.client.post('/api/owners/search', json={'query': 'Sobha', 'page': 1}).get_json()
        second = self.client.post('/api/owners/search', json={'query': 'Sobha', 'page': 2}).get_json()
        self.assertEqual(len(first['results']), 12)
        self.assertTrue(set(g['unit'] for g in first['results']).isdisjoint(g['unit'] for g in second['results']))
        result = self.client.post('/api/owners/search', json={'query': 'zzzz-no-such-record-zzzz'}).get_json()
        self.assertEqual(result['results'], [])

    def test_validation(self):
        for data in ({'unit': '../4102'}, {'unit': '4102', 'price': '-3'}, {'unit': '4102', 'facing': 'invalid'}, {'unit': []}, {'unit': '4102', 'include_owners': 'true'}):
            self.assertEqual(self.client.post('/api/generate', json=data).status_code, 400)
        self.assertEqual(self.client.post('/api/generate', json={'unit': '99999'}).status_code, 422)

    def test_combine_requires_both_sources(self):
        with patch.object(owners, 'for_unit', return_value=[]):
            response = self.client.post('/api/generate', json={'unit': '4102', 'include_owners': True})
            self.assertEqual(response.status_code, 422)
        response = self.client.post('/api/owners/unit', json={'unit': '99999'}).get_json()
        self.assertFalse(response['can_combine'])

    def test_pdf_generation_and_record_integrity(self):
        out = Path('tmp/pdfs')
        out.mkdir(parents=True, exist_ok=True)
        for unit, combine, filename in [('4102', False, 'wing4-brochure.pdf'), ('4102', True, 'combined.pdf')]:
            response = self.client.post('/api/generate', json={'unit': unit, 'facing': 'East', 'price': '3.9', 'include_owners': combine})
            self.assertEqual(response.status_code, 200, response.get_json(silent=True))
            self.assertEqual(response.mimetype, 'application/pdf')
            self.assertIn('attachment', response.headers['Content-Disposition'])
            self.assertEqual(response.headers['Cache-Control'], 'no-store')
            (out / filename).write_bytes(response.data)
            with pymupdf.open(stream=response.data, filetype='pdf') as doc:
                self.assertEqual(len(doc), 3 + (len(owners.for_unit(unit)) if combine else 0))
                self.assertIn('2481.18', doc[0].get_text())
                self.assertIn(unit, doc[0].get_text())
                if combine:
                    for index, row in enumerate(owners.for_unit(unit)):
                        text = doc[3 + index].get_text()
                        for key, value in row.items():
                            self.assertIn(key, text)
                            if value:
                                self.assertIn(value, text)
                for index, page in enumerate(doc):
                    self.assertIn('%d / %d' % (index + 1, len(doc)), page.get_text())
                    page.get_pixmap(matrix=pymupdf.Matrix(1.3, 1.3)).save(out / ('%s-%d.png' % (filename, index + 1)))


if __name__ == '__main__':
    unittest.main()

