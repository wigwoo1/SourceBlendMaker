import unittest
from unittest.mock import patch
from particle_initializer_history import initialize


class InitializerHistoryTests(unittest.TestCase):
    def test_noise_reads_position_at_its_authored_point(self):
        noise = {'function': 'Remap Noise to Scalar', 'parameters': {}}
        spawn = {'function': 'Position From Control Points', 'parameters': {}}
        calls = []
        def sample(parameters, position, creation, tables):
            calls.append(position)
            return 2
        with patch('particle_noise_scalar.sample', sample):
            fields, position, history = initialize([noise, spawn, noise], {3: 1, 8: 0}, (0, 0, 0),
                                                   lambda *args: ({}, (10, 20, 30)), [])
        self.assertEqual(calls, [(0, 0, 0), (10, 20, 30)])
        self.assertEqual(history[0]['position'], (0, 0, 0))
        self.assertEqual(position, (10, 20, 30))

    def test_later_random_write_replaces_noise_and_offset_reads_current_radius(self):
        noise = {'function': 'Remap Noise to Scalar', 'parameters': {}}
        radius = {'function': 'Radius Random', 'parameters': {}}
        offset = {'function': 'Position Modify Offset Random', 'parameters': {}}
        def sampler(index, module, fields, position):
            if module['function'] == 'Radius Random':
                return {3: 6}, None
            return {}, (position[0] + fields[3], 0, 0)
        with patch('particle_noise_scalar.sample', return_value=2):
            fields, position, _ = initialize([noise, offset, radius, offset], {3: 1, 8: 0}, (0, 0, 0), sampler, [])
        self.assertEqual(position, (8, 0, 0))
        self.assertEqual(fields[3], 6)

    def test_disabled_writes_and_unknown_attribute(self):
        disabled = {'function': 'Radius Random', 'parameters': {'operator enabled': False}}
        initialize([disabled], {3: 1}, (0, 0, 0), lambda *args: self.fail('Disabled write sampled'))
        enabled = {**disabled, 'parameters': {}}
        with self.assertRaises(ValueError):
            initialize([enabled], {3: 1}, (0, 0, 0), lambda *args: ({99: 2}, None))


if __name__ == '__main__':
    unittest.main()
