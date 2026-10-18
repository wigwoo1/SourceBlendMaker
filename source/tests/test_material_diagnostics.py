import unittest
from material_diagnostics import unresolved_reason

class MaterialDiagnosticsTests(unittest.TestCase):
    def test_unresolved_patch_identifies_base(self):
        class Vmt:
            shader = 'patch'
            def get_string(self, key):
                return 'materials/tile/tilefloor_c.vmt'
        self.assertEqual(unresolved_reason(Vmt()),
                         'Patch base material could not be resolved: materials/tile/tilefloor_c.vmt')

    def test_other_shader_is_identified(self):
        class Vmt:
            shader = 'Water'
        self.assertEqual(unresolved_reason(Vmt()), 'Material shader conversion incomplete: Water')
