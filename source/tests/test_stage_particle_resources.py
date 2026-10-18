import tempfile,unittest
from pathlib import Path
from stage_release import stage


class ParticleResourceStagingTests(unittest.TestCase):
    def test_noise_tables_are_staged_but_diagnostic_json_is_not(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'source';source.mkdir();target=root/'staged'
            (source/'worker.py').write_text('')
            (source/'particle_noise_tables.json').write_text('{"tables":[]}')
            (source/'VALIDATION.json').write_text('{"historical":true}')
            stage(source,target)
            self.assertEqual((target/'particle_noise_tables.json').read_bytes(),(source/'particle_noise_tables.json').read_bytes())
            self.assertFalse((target/'VALIDATION.json').exists())


if __name__=='__main__':unittest.main()
