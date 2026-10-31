"""Synthetic FIXTURE tests only; no artificial law data in the real bundle."""
from pathlib import Path
from types import SimpleNamespace
import io
import tempfile
import unittest
from unittest.mock import patch

from src import subset_bm25 as bm
from src.experimental_dataset import load


class SubsetBM25Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = load(bm.baseline.DEFAULT_CONFIG)
        cls.projected = [
            {'record_id': 'FIXTURE-A', 'record_type': 'chunk.v1', 'text_for_search': 'đường xe', 'content_sha256': 'synthetic'},
            {'record_id': 'FIXTURE-B', 'record_type': 'table-retrieval.v1', 'text_for_search': 'đường xe', 'content_sha256': 'synthetic'},
            {'record_id': 'FIXTURE-C', 'record_type': 'source-retrieval.v1', 'text_for_search': 'tốc độ 60', 'content_sha256': 'synthetic'}]
        engine, _ = bm.composition.create(cls.projected, cls.cfg)
        cls.state = {'retriever': engine, 'config': cls.cfg, 'mapping': [
            {'record_id': p['record_id'], 'record_type': p['record_type'], 'source_id': s, 'law_id': s + '/FIXTURE',
             'unit_id': 'FIXTURE-' + s, 'citation_path': 'SYNTHETIC ONLY'}
            for p, s in zip(cls.projected, ['A', 'B', 'C'])], 'consumer': SimpleNamespace(sources={
                k: {'law_id': k + '/FIXTURE'} for k in ['A', 'B', 'C', 'EMPTY']})}

    def test_stable_tie_and_no_padding(self):
        result = bm.search_loaded(self.state, 'đường', 10)
        self.assertEqual([h['record_id'] for h in result['results']], ['FIXTURE-A', 'FIXTURE-B'])
        self.assertTrue(all(h['score'] > 0 for h in result['results']))

    def test_source_filter_before_top_k(self):
        result = bm.search_loaded(self.state, 'đường', 1, source_id='B')
        self.assertEqual([h['record_id'] for h in result['results']], ['FIXTURE-B'])
        self.assertEqual(result['results'][0]['rank'], 1)

    def test_type_and_law_filter(self):
        result = bm.search_loaded(self.state, 'đường', 1, record_type='table-retrieval.v1', law_id='B/FIXTURE')
        self.assertEqual(result['results'][0]['record_id'], 'FIXTURE-B')
        self.assertEqual(bm.search_loaded(self.state, 'đường', 10, source_id='A', law_id='B/FIXTURE')['results'], [])

    def test_empty_valid_source_and_oov(self):
        self.assertEqual(bm.search_loaded(self.state, 'đường', source_id='EMPTY')['results'], [])
        self.assertEqual(bm.search_loaded(self.state, 'zzzxxyyfixture')['results'], [])

    def test_empty_and_punctuation_queries(self):
        for query in ['', '  \t\n', '!!!', '%']:
            with self.subTest(query=query), self.assertRaises(ValueError):
                bm.search_loaded(self.state, query)

    def test_invalid_top_k(self):
        for value in [0, -1, True, 1.0, '2']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                bm.search_loaded(self.state, 'đường', value)

    def test_invalid_filters(self):
        for kwargs in [{'source_id': 'UNKNOWN'}, {'law_id': 'UNKNOWN'}, {'record_type': 'encoder-view'}, {'source_id': []}]:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                bm.search_loaded(self.state, 'đường', **kwargs)

    def test_vietnamese_nfc_without_accent_removal(self):
        original = 'đường'
        self.assertEqual(bm.search_loaded(self.state, original)['results'], bm.search_loaded(self.state, 'đường')['results'])
        self.assertEqual(bm.search_loaded(self.state, 'duong')['results'], [])

    def test_three_types_keep_identity(self):
        for query, kind in [('đường', 'chunk.v1'), ('đường', 'table-retrieval.v1'), ('tốc', 'source-retrieval.v1')]:
            h = bm.search_loaded(self.state, query, record_type=kind)['results'][0]
            self.assertEqual(h['record_type'], kind)
            self.assertEqual(h['dataset_version'], bm.DATASET)
            self.assertFalse(h['release_eligible'])

    def test_missing_index_does_not_create_output(self):
        with tempfile.TemporaryDirectory() as temp:
            missing = Path(temp) / 'absent'
            with self.assertRaises(FileNotFoundError):
                bm.load_index(missing)
            self.assertFalse(missing.exists())

    def test_output_must_be_new_and_outside_immutable(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaises(ValueError): bm.new_output(root)
            with self.assertRaises(ValueError): bm.new_output(root / 'BAD-output', root)
            self.assertFalse((root / 'BAD-output').exists())

    def test_projection_recipe_never_encoder_view(self):
        self.assertEqual(set(bm.RECIPES), set(bm.COUNTS))
        self.assertTrue(all('record.text_for_search:verbatim' in r for r in bm.RECIPES.values()))

    def test_redirected_windows_cli_uses_utf8_without_changing_text(self):
        buffer = io.BytesIO()
        stream = io.TextIOWrapper(buffer, encoding='cp1252')
        try:
            with patch.object(bm.sys, 'stdout', stream), patch.object(bm, 'validate', return_value={'text': 'tốc độ, đường'}):
                self.assertEqual(bm.main(['validate', '--index', 'SYNTHETIC-FIXTURE']), 0)
            stream.flush()
            self.assertIn('tốc độ, đường', buffer.getvalue().decode('utf8'))
        finally:
            stream.detach()


if __name__ == '__main__':
    unittest.main()
