import copy
import random
import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from particle_bake import plan, birth_ranges
from test_particle_initial_only import definition


class DefinitionLifetimeTests(unittest.TestCase):
    def effect(self):
        effect = definition(2)
        effect['modules']['initializers'] = [m for m in effect['modules']['initializers']
                                              if m['function'] != 'Lifetime Random']
        return effect

    def test_absent_initializer_uses_definition_default_without_random_draw(self):
        effect = self.effect()
        original = copy.deepcopy(effect)
        config = plan(effect)
        rng = random.Random(17)
        expected = random.Random(17)
        self.assertEqual(birth_ranges(config, rng), (1., 1.))
        self.assertEqual(rng.random(), expected.random())
        self.assertEqual(config['definition_lifetime'], 1.)
        self.assertEqual(effect, original)

    def test_authored_definition_lifetime_controls_range(self):
        effect = self.effect()
        effect['parameters']['lifetime'] = 2.75
        self.assertEqual(plan(effect)['lifetime_range'], [2.75, 2.75])

    def test_explicit_initializer_overrides_definition_constant(self):
        effect = definition(2)
        effect['parameters']['lifetime'] = 17.
        config = plan(effect)
        self.assertEqual(config['lifetime_range'], [1., 1.])
        self.assertIsNone(config['definition_lifetime'])

    def test_invalid_definition_lifetime_is_rejected(self):
        for value in (-1., 0., float('nan'), float('inf')):
            effect = self.effect()
            effect['parameters']['lifetime'] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                plan(effect)
