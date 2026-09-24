import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from capdata import load_tables, catalog
from capdata.__main__ import extract_verified

class ReleaseTests(unittest.TestCase):
    def test_training_default_does_not_read_confirmation(self):
        with tempfile.TemporaryDirectory() as tmp:
            desc=catalog()['datasets']['public_rules_holdout']
            target=Path(tmp)/desc['path'];target.parent.mkdir(parents=True)
            target.write_text(''.join(json.dumps(dict(partition=p,table_id=p))+'\n' for p in ['train','val','test','holdout']))
            self.assertEqual([r['table_id'] for r in load_tables('public_rules_holdout',root=tmp)],['train'])
            with self.assertRaises(ValueError):load_tables('public_rules_holdout',partition='confirmation',root=tmp)

    def test_archive_rejects_escape_and_changed_payload(self):
        for name,content,wanted in [('../escape',b'x',b'x'),('safe.txt',b'bad',b'good')]:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                arc=Path(tmp)/'a.tar.gz'
                with tarfile.open(arc,'w:gz') as t:
                    m=tarfile.TarInfo(name);m.size=len(content);t.addfile(m,io.BytesIO(content))
                with self.assertRaises(ValueError):extract_verified(arc,Path(tmp)/'out',[dict(path='safe.txt',bytes=len(wanted),sha256=hashlib.sha256(wanted).hexdigest())])
                self.assertFalse((Path(tmp)/'escape').exists())

    def test_extraction_is_idempotent_and_refuses_modified_local_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            arc=Path(tmp)/'a.tar.gz';data=b'recorded evidence'
            with tarfile.open(arc,'w:gz') as t:
                m=tarfile.TarInfo('data/x.txt');m.size=len(data);t.addfile(m,io.BytesIO(data))
            spec=[dict(path='data/x.txt',bytes=len(data),sha256=hashlib.sha256(data).hexdigest())]
            out=Path(tmp)/'out';extract_verified(arc,out,spec);extract_verified(arc,out,spec)
            (out/'data/x.txt').write_text('local edit')
            with self.assertRaises(FileExistsError):extract_verified(arc,out,spec)
            self.assertEqual((out/'data/x.txt').read_text(),'local edit')

if __name__=='__main__':unittest.main()
