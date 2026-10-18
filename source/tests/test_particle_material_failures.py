import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from particles import ParticleTextureError,material_failure

class ParticleMaterialFailures(unittest.TestCase):
    def test_missing_asset_is_distinct_from_texture_format(self):
        self.assertEqual(material_failure('test.vmt',FileNotFoundError('test.vtf'))['failure_category'],'missing_asset')
        invalid=material_failure('test.vmt',ParticleTextureError('materials/test.vtf','Invalid VTF header'))
        self.assertEqual(invalid['failure_category'],'invalid_texture_data')
        self.assertIn('materials/test.vtf',invalid['reason'])
        unsupported=material_failure('test.vmt',ParticleTextureError('materials/test.vtf','Unsupported particle-sheet layout'))
        self.assertEqual(unsupported['failure_category'],'unsupported_texture_format')

if __name__=='__main__':unittest.main()
