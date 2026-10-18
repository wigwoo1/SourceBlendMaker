import unittest
from particle_noise_bake_adapter import prepare


class NoisePlanTests(unittest.TestCase):
    def plan(self, definition, **kwargs):
        self.assertFalse(any(m['function']=='Remap Noise to Scalar' for m in definition['modules']['initializers']))
        return {'lifetime_range': [2, 2], 'radius_range': [4, 4]}

    def definition(self, parameters):
        return {'modules': {'initializers': [{'function': 'Remap Noise to Scalar', 'parameters': parameters}]}}

    def test_absolute_noise_includes_zero_in_lifetime_bounds(self):
        config = prepare(self.definition({'output field': 1, 'absolute value': True, 'output maximum': 8}), self.plan)
        self.assertEqual(config['lifetime_range'], [0, 8])

    def test_inverted_signed_noise_can_exceed_authored_endpoint(self):
        config = prepare(self.definition({'invert absolute value': True, 'output minimum': 2, 'output maximum': 10}), self.plan)
        self.assertEqual(config['radius_range'], [4, 14])

    def test_unrepresented_context_and_negative_lifetime_rejected(self):
        for p in ({'output field': 20}, {'output field': 1, 'output minimum': -2}, {'world time noise coordinate scale': 1}):
            with self.assertRaises(ValueError):
                prepare(self.definition(p), self.plan)

    def test_velocity_noise_is_allowed_alongside_ordered_scalar_noise(self):
        definition = self.definition({'output field': 3, 'output minimum': 1, 'output maximum': 3})
        definition['modules']['initializers'].append({
            'function': 'Velocity Noise',
            'parameters': {
                'output minimum': [-10, -10, -10],
                'output maximum': [10, 10, 10],
            },
        })
        config = prepare(definition, self.plan)
        self.assertTrue(config['ordered_noise_birth'])
        self.assertTrue(config['source_velocity_noise_birth'])
        self.assertEqual(config['initializer_order'],[0,1])

    def test_velocity_planner_filters_later_primary_writes_before_calculating_bounds(self):
        definition = self.definition({'output field':3,'output minimum':1,'output maximum':3})
        definition['modules']['initializers'] += [
            {'function':'Lifetime Random','parameters':{'lifetime_min':2,'lifetime_max':4}},
            {'function':'Lifetime Random','parameters':{'lifetime_min':20,'lifetime_max':40}},
            {'function':'Velocity Noise','parameters':{}}]
        def planner(cleaned,**kw):
            self.assertEqual([m['parameters']['lifetime_min'] for m in cleaned['modules']['initializers']
                if m['function']=='Lifetime Random'],[2])
            return {'lifetime_range':[2,4],'radius_range':[1,1]}
        self.assertEqual(prepare(definition,planner)['initializer_order'],[0,1,3])

    def test_scalar_only_path_keeps_existing_execution_behavior(self):
        self.assertIsNone(prepare(self.definition({}),self.plan)['initializer_order'])
