import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from particle_names import canonical,normalize

class ParticleNameTests(unittest.TestCase):
    def test_supported_case_variants(self):
        self.assertEqual(canonical('remap initial scalar'),'Remap Initial Scalar')
        self.assertEqual(canonical('MOVEMENT BASIC'),'Movement Basic')
        self.assertEqual(canonical('RENDER_ROPE'),'render_rope')

    def test_unknown_names_are_not_guessed(self):
        self.assertEqual(canonical('radius_random'),'radius_random')
        self.assertEqual(canonical('Unsupported Operator'),'Unsupported Operator')

    def test_original_metadata_and_parameters_are_preserved(self):
        parameters={'operator enabled':False,'output minimum':7}
        original={'name':'test','modules':{'initializers':[{'function':'remap initial scalar','parameters':parameters}]}}
        normalized=normalize(original)
        module=normalized['modules']['initializers'][0]
        self.assertEqual(module['function'],'Remap Initial Scalar')
        self.assertEqual(module['source_function'],'remap initial scalar')
        self.assertIs(module['parameters'],parameters)
        self.assertEqual(original['modules']['initializers'][0]['function'],'remap initial scalar')
        self.assertEqual(normalize(normalized),normalized)
