import unittest
from types import SimpleNamespace

from particle_parent_attribute import Initializer, NAME, prepare
from particle_parent_collection import Collection
from particle_parent_retention import required


def module(name, **parameters):
    return {'function': name, 'parameters': parameters}


class ParentAttributeTests(unittest.TestCase):
    def test_installed_lifetime_and_quarter_radius_use_independent_cursors(self):
        life = Initializer({'Inherited Field': 1})
        radius = Initializer({'Scale': .25})
        self.assertEqual(life.initialize([2., 4.]), 2.)
        self.assertEqual(life.initialize([2., 4.]), 4.)
        self.assertEqual(radius.initialize([20., 40.]), 5.)
        self.assertEqual(radius.initialize([20., 40.]), 10.)

    def test_empty_parent_noop_does_not_advance(self):
        operation = Initializer({})
        self.assertIsNone(operation.initialize(None))
        self.assertIsNone(operation.initialize(()))
        self.assertEqual(operation.cursor, 0)

    def test_cursor_wrap_discards_excess_and_random_selection_is_discrete(self):
        operation = Initializer({'Particle Increment Amount': 3})
        self.assertEqual(operation.initialize([10., 20.]), 10.)
        self.assertEqual(operation.initialize([10., 20.]), 10.)
        operation = Initializer({'Random Parent Particle Distribution': True})
        self.assertEqual(operation.initialize([10., 20., 30.], .5), 20.)

    def test_float32_read_before_multiply(self):
        self.assertEqual(Initializer({'Scale': .5}).initialize([16777217.]), 8388608.)

    def test_unverified_fields_gates_and_signed_scaling_rejected(self):
        for parameters in ({'Inherited Field': 7}, {'Inherited Field': True},
                           {'Particle Increment Amount': .5}, {'Scale': -1},
                           {'Scale': float('nan')}, {'operator start fadein': .2},
                           {'run for killed parent particles': False}):
            with self.subTest(parameters=parameters):
                with self.assertRaises(ValueError):
                    Initializer(parameters)

    def definition(self, initializers=None, emitters=None):
        return {'modules': {'initializers': initializers or [
            module('Position From Parent Particles'), module(NAME, **{'Inherited Field': 1}),
            module(NAME, Scale=.25)], 'emitters': emitters or []}}

    def test_repeated_inheritance_is_preserved_in_authored_order(self):
        operations = prepare(self.definition())
        self.assertEqual([(op.field, op.scale) for op in operations], [(1, 1.), (3, .25)])
        self.assertEqual(required([dict(self.definition(), parent_instance_id=7)]), {7})

    def test_later_initializers_are_not_silently_reordered(self):
        definition = self.definition()
        definition['modules']['initializers'].append(module('Radius Random'))
        with self.assertRaisesRegex(ValueError, 'follow other'):
            prepare(definition)
        definition['modules']['initializers'][-1]['parameters']['operator enabled'] = False
        self.assertEqual(len(prepare(definition)), 2)

    def test_incomplete_context_and_maintained_lifecycle_are_gated(self):
        with self.assertRaisesRegex(ValueError, 'parent-position'):
            prepare(self.definition([module(NAME)]))
        with self.assertRaisesRegex(ValueError, 'Maintained emission'):
            prepare(self.definition(emitters=[module('emit to maintain count')]))

    def collection(self):
        births = [SimpleNamespace(index=9, simulation_time=0.),
                  SimpleNamespace(index=2, simulation_time=1.)]
        return Collection(3, births, {9: 2., 2: 4.}, {9: (0, 0, 0), 2: (0, 0, 0)},
                          lambda birth, age, life: ((0, 0, 0), None, None, None), 1.,
                          radius_sampler=lambda birth, age, life: birth.index + age * 10)

    def test_active_scalar_buffers_match_parent_position_order(self):
        collection = self.collection()
        self.assertEqual(collection.snapshot(1.5, .1).particle_ids, (9, 2))
        self.assertEqual(collection.scalar_values(1, 1.5), (2., 4.))
        self.assertEqual(collection.scalar_values(3, 1.5), (24., 7.))

    def test_parent_expiry_and_unborn_parents_are_excluded(self):
        collection = self.collection()
        self.assertEqual(collection.scalar_values(1, .5), (2.,))
        self.assertEqual(collection.snapshot(2., .1).particle_ids, (2,))
        self.assertEqual(collection.scalar_values(1, 2.), (4.,))
        self.assertEqual(collection.scalar_values(3, 5.), ())

    def test_live_radius_is_resampled_at_each_birth_clock(self):
        collection = self.collection()
        self.assertEqual(collection.scalar_values(3, .5), (14.,))
        self.assertEqual(collection.scalar_values(3, .6), (15.,))

    def test_missing_radius_history_fails_instead_of_using_birth_radius(self):
        collection = self.collection()
        collection.radius_sampler = None
        with self.assertRaisesRegex(ValueError, 'unavailable'):
            collection.scalar_values(3, 1.)
