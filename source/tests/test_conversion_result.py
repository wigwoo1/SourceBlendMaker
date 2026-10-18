import sys,unittest,tempfile,gzip
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from conversion_result import validate_result

class ResultTests(unittest.TestCase):
    def test_completed_and_compressed_headers(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'scene.blend';report={'run_id':'current','status':'partial'}
            for content in (b'BLENDER-v502',gzip.compress(b'BLENDER-v502')):
                path.write_bytes(content);validate_result(path,report,'current')
    def test_stale_incomplete_missing_and_invalid(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'scene.blend';path.write_bytes(b'BLENDER-v502')
            for report in ({},{'run_id':'old','status':'converted'},{'run_id':'current','status':'running'}):
                with self.assertRaises(ValueError):validate_result(path,report,'current')
            report={'run_id':'current','status':'converted'}
            for content in (b'',b'not a Blender project'):
                path.write_bytes(content)
                with self.assertRaises(ValueError):validate_result(path,report,'current')
            path.unlink()
            with self.assertRaises(ValueError):validate_result(path,report,'current')
