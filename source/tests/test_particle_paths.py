import unittest
from particle_paths import recorded_pcf_path

class ParticlePathTests(unittest.TestCase):
    def test_moved_windows_installation_uses_selected_mounts(self):
        self.assertEqual(recorded_pcf_path(r'D:\old\SourceFilmmaker\game\workshop\particles\pack\fire.pcf'),'particles/pack/fire.pcf')
    def test_relative_paths_stay_relative(self):
        self.assertEqual(recorded_pcf_path(r'particles\fire.pcf'),'particles/fire.pcf')
    def test_absolute_unknown_and_traversal_are_rejected(self):
        for path in ('D:/other/fire.pcf','particles/../secret.pcf','D:/game/particles/../secret.pcf'):
            with self.assertRaises(ValueError):recorded_pcf_path(path)
