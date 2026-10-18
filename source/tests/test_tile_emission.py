import unittest
from tile_emission import is_tile
class TileEmissionTests(unittest.TestCase):
    def test_exact_source_surface_only(self):
        self.assertTrue(is_tile('materials/models/tools/terrain_plane/skin0_vertexlitgeneric.vmt'))
        self.assertTrue(is_tile('MODELS\\TOOLS\\TERRAIN_PLANE\\SKIN0_VERTEXLITGENERIC'))
        self.assertFalse(is_tile('models/tools/terrain_plane/other'))
        self.assertFalse(is_tile('models/character/body'))
