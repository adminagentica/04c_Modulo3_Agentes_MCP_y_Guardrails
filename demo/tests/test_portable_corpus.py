"""El corpus debe funcionar después de clonar y desde cualquier directorio de trabajo."""
from pathlib import Path
import os,sys,tempfile,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import rag_client

class PortableCorpusTests(unittest.TestCase):
    def test_default_corpus_is_relative_and_included(self):
        configured=Path(rag_client.CONFIG['corpus_dir'])
        self.assertFalse(configured.is_absolute())
        corpus=(Path(rag_client.__file__).resolve().parents[1]/configured).resolve()
        self.assertTrue((corpus/'lineage_manifest.json').is_file())
        self.assertEqual(len(list(corpus.glob('*.docx'))),4)
    def test_source_fingerprint_independent_of_working_directory(self):
        before=rag_client.source_fingerprint();old=Path.cwd()
        with tempfile.TemporaryDirectory() as folder:
            try:
                os.chdir(folder)
                self.assertEqual(rag_client.source_fingerprint(),before)
            finally:os.chdir(old)
        self.assertRegex(before,r'^[a-f0-9]{64}$')
