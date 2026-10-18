import sys,unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from particles import Definitions

class LookupCacheTests(unittest.TestCase):
    def test_missing_names_are_cached_case_insensitively_per_conversion(self):
        class Mounts:
            def __init__(self):self.calls=0
            def glob(self,pattern):self.calls+=1;return iter(())
        mounts=Mounts();assets=SimpleNamespace(cm=mounts);definitions=Definitions(assets)
        for name in ('absent','ABSENT','absent'):
            with self.assertRaises(FileNotFoundError):definitions.find(name)
        self.assertEqual(mounts.calls,2)
        self.assertEqual(definitions.lookup_summary(),{'parsed_pcf_files':0,'definition_names':0,'unresolved_names':['absent'],'parse_errors':[]})
        with self.assertRaises(FileNotFoundError):Definitions(assets).find('absent')
        self.assertEqual(mounts.calls,4)

if __name__=='__main__':unittest.main()
