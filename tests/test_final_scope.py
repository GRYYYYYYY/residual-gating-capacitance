import json
from pathlib import Path
import unittest
from capdata.__main__ import packages, files, package_key
ROOT=Path(__file__).resolve().parents[1]

class FinalScopeTests(unittest.TestCase):
    def test_only_final_download_scope(self):
        self.assertEqual(package_key('models'), 'models-v1.1.0')
        self.assertTrue(all(v['tag']=='v1.1.0' for v in packages().values()))
        self.assertFalse(any('historical' in k for k in packages()))
        self.assertFalse(any('to_freepdk15' in r['path'] for r in files()))
        with self.assertRaises(ValueError):package_key('historical-evidence')

    def test_final_presentation_and_model_mapping(self):
        wanted={'public','reference','to_asap7'}
        for name in ['paper_models.json','selected_models.json']:
            self.assertEqual(set(json.loads((ROOT/'configs'/name).read_text())),wanted)
        self.assertFalse((ROOT/'results/expected_tables').exists())
        self.assertFalse((ROOT/'analysis/build_tables.py').exists())

if __name__=='__main__':unittest.main()
