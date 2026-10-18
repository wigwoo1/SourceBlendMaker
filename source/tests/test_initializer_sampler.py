import random
import unittest
from particle_initializer_history import initialize
from particle_initializer_sampler import bind


class SamplerTests(unittest.TestCase):
    def test_omitted_lifetime_endpoints_use_installed_zero_defaults(self):
        sampler = bind(random.Random(1),None,{})
        self.assertEqual(sampler(0,{'function':'Lifetime Random','parameters':{}},{1:5},(0,0,0))[0],{1:0})

    def test_lifetime_and_radius_last_write_wins_without_losing_random_draws(self):
        modules = [{'function': 'Radius Random', 'parameters': {'radius_min': 2, 'radius_max': 4}},
                   {'function': 'Lifetime Random', 'parameters': {'lifetime_min': 1, 'lifetime_max': 3}},
                   {'function': 'Radius Random', 'parameters': {'radius_min': 8, 'radius_max': 10}}]
        reference = random.Random(12)
        first = reference.uniform(2, 4)
        lifetime = reference.uniform(1, 3)
        radius = reference.uniform(8, 10)
        fields, _, history = initialize(modules, {1: 1, 3: 1}, (0, 0, 0), bind(random.Random(12), None, {}))
        self.assertEqual(fields, {1: lifetime, 3: radius})
        self.assertEqual(history[0]['fields'][3], first)

    def test_scene_callback_gets_current_noise_radius(self):
        tables = [list(range(256)) for _ in range(3)] + [[.75] * 256]
        seen = []
        def spatial(index, module, fields, position):
            seen.append(fields[3])
            return {}, (fields[3], 0, 0)
        modules = [{'function': 'Remap Noise to Scalar', 'parameters': {'output maximum': 4}},
                   {'function': 'Position Modify Offset Random', 'parameters': {}}]
        _, position, _ = initialize(modules, {3: 1, 8: 0}, (0, 0, 0), bind(random.Random(1), spatial, {}), tables)
        self.assertEqual(seen, [3])
        self.assertEqual(position, (3, 0, 0))

    def test_spin_noise_field_is_not_angle_converted(self):
        from particle_noise_scalar import sample
        tables = [list(range(256)) for _ in range(3)] + [[.75] * 256]
        self.assertEqual(sample({'output field': 5, 'output maximum': 180}, (0, 0, 0), 0, tables), 135)
