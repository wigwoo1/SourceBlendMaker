import unittest
from particle_spatial_force_context import bind

def module(name,**parameters):return {'function':name,'parameters':parameters}

class SpatialContextTests(unittest.TestCase):
    def test_ordered_movement_gate_checks_drag_and_enabled_locks(self):
        from particle_spatial_force_context import ordered_movement_supported
        def definition(ops):return {'modules':{'operators':ops}}
        for drag in (0.,.2,.9999):
            self.assertTrue(ordered_movement_supported(definition([module('Movement Basic',drag=drag)])))
        for drag in (-1.,1.,float('nan')):
            self.assertFalse(ordered_movement_supported(definition([module('Movement Basic',drag=drag)])))
        self.assertFalse(ordered_movement_supported(definition([module('Movement Basic'),module('Movement Basic')])))
        self.assertFalse(ordered_movement_supported(definition([module('Movement Basic'),module('Movement Lock to Control Point')])))
        self.assertTrue(ordered_movement_supported(definition([module('Movement Basic'),module('Movement Lock to Control Point')]),allow_translation_lock=True))
        self.assertTrue(ordered_movement_supported(definition([module('Movement Basic'),module('Movement Lock to Control Point',**{'operator enabled':False})])))
    def test_twist_translation_scale_and_collection_clock(self):
        seen=[]
        def target(cp,time):
            seen.append((cp,time))
            return (100.,-20.,5.)
        force=bind([module('Twist around axis',**{'amount of force':4.,'control point':3})],
                   (100.,-20.,5.),.25,7.,target)
        self.assertEqual(force(.5,(.25,0.,0.)),(0.,-1.,0.))
        self.assertEqual(seen,[(3,7.5)])

    def test_plane_uses_source_distance_and_adds_forces(self):
        plane=module('Force based on distance from plane',**{
            'Max Distance from plane':10.,'Force at Max distance':(0.,0.,8.)})
        force=bind([plane,plane],(0.,0.,10.),2.,0.,lambda cp,time:(0.,0.,0.))
        self.assertEqual(force(1.,(0.,0.,0.)),(0.,0.,16.))

    def test_disabled_force_does_not_read_control_point(self):
        force=bind([module('Twist around axis',**{'operator enabled':False})],(0.,)*3,1.,0.,
                   lambda cp,time:self.fail('Disabled force read a control point'))
        self.assertEqual(force(0.,(0.,)*3),(0.,)*3)

    def test_invalid_context_and_unsupported_force_fail_explicitly(self):
        for scale in (0.,-1.,float('nan')):
            with self.assertRaises(ValueError):bind([],(0.,)*3,scale,0.,None)
        with self.assertRaises(ValueError):bind([module('unknown force')],(0.,)*3,1.,0.,None)

    def test_pull_source_distance_and_component_scaling(self):
        pull=module('Pull towards control point',**{'amount of force':16.,'falloff power':2.,
                                                  'component scale':(1.,2.,1.)})
        force=bind([pull],(10.,20.,0.),2.,0.,lambda cp,time:(10.,28.,0.))
        # Four Source units away: 16 / 4**2, doubled Y component, two Blender units per Source unit.
        self.assertEqual(force(.1,(0.,0.,0.)),(0.,4.,0.))

    def test_pull_rejects_unimplemented_local_scaling(self):
        with self.assertRaises(ValueError):
            bind([module('Pull towards control point',**{'scale in local space':True})],(0.,)*3,1.,0.,None)

    def test_pull_and_twist_keep_their_own_equations_in_either_order(self):
        pull=module('Pull towards control point',**{'amount of force':2.,'falloff power':0.})
        twist=module('twist around axis',**{'amount of force':4.})
        for modules in ([pull,twist],[twist,pull]):
            force=bind(modules,(1.,0.,0.),1.,0.,lambda cp,time:(0.,)*3)
            self.assertEqual(force(.1,(0.,)*3),(-2.,-4.,0.))

    def test_ordered_pull_history_matches_constant_force_closed_form(self):
        from particle_vector_history import History
        step=1/128
        force=bind([module('Pull towards control point',**{'amount of force':4.,'falloff power':0.})],
                   (100.,0.,0.),1.,5.,lambda cp,time:(0.,)*3)
        history=History([module('Movement Basic')],(0.,)*3,(0.,)*3,(.5,)*3,10.,
                        step=step,spatial_acceleration=force)
        # Constant direction until the target is crossed. The decoded position
        # buffer recurrence adds a*dt^2 each tick, giving a triangular sum.
        for ticks in (1,8,16,4,20):
            position,previous,color=history.query(ticks*step)
            self.assertEqual(position,(-4.*step*step*ticks*(ticks+1)/2,0.,0.))
            self.assertEqual(previous,(-4.*step*step*ticks*(ticks-1)/2,0.,0.))
            self.assertEqual(color,(.5,)*3)
            self.assertLessEqual(len(history.samples),8)

if __name__=='__main__':unittest.main()
