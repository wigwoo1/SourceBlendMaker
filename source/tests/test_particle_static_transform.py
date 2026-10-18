import sys
import unittest
from pathlib import Path
from types import SimpleNamespace as NS

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from particle_static_transform import transform_is_static,controls_are_static


def curve(path,values,modifiers=()):
    return NS(data_path=path,modifiers=modifiers,
              keyframe_points=[NS(co=NS(y=value)) for value in values],sampled_points=[])


def obj(parent=None,curves=(),constraints=(),drivers=(),nla=(),parent_type='OBJECT'):
    action=NS(fcurves=list(curves)) if curves else None
    animation=NS(action=action,drivers=list(drivers),nla_tracks=list(nla)) if action or drivers or nla else None
    return NS(parent=parent,parent_type=parent_type,constraints=list(constraints),
              rigid_body=None,animation_data=animation)


class StaticParticleTransformTests(unittest.TestCase):
    def test_virtual_time_dependent_control_is_never_sampled_as_static(self):
        candidate=obj();candidate.sfm_time_dependent=True
        self.assertFalse(transform_is_static(candidate))

    def test_unanimated_and_constant_transform_chains_are_static(self):
        parent=obj(curves=[curve('location',[0.,0.])])
        child=obj(parent=parent,curves=[curve('location',[1.,1.]),curve('rotation_quaternion',[1.,1.])])
        self.assertTrue(transform_is_static(child))
        self.assertTrue(controls_are_static({'cp':child}))

    def test_motion_unknown_channels_and_modifiers_fail_closed(self):
        cases=(
            obj(curves=[curve('location',[0.,1.])]),
            obj(curves=[curve('location',[0.,0.],modifiers=[object()])]),
            obj(curves=[curve('pose.bones[\"root\"].location',[0.,0.])]),
            obj(constraints=[object()]),
            obj(drivers=[object()]),
            obj(nla=[object()]),
            obj(parent=obj(),parent_type='BONE'),
        )
        for candidate in cases:
            with self.subTest(candidate=candidate):self.assertFalse(transform_is_static(candidate))

    def test_parent_animation_is_included_in_world_transform(self):
        moving_parent=obj(curves=[curve('location',[0.,2.])])
        self.assertFalse(transform_is_static(obj(parent=moving_parent)))

    def test_action_layer_channelbags_are_inspected(self):
        channelbag=NS(fcurves=[curve('location',[0.,0.])])
        slot=object()
        strip=NS(channelbag=lambda requested:channelbag if requested is slot else None)
        action=NS(slots=[slot],layers=[NS(strips=[strip])])
        animation=NS(action=action,action_slot=slot,drivers=[],nla_tracks=[])
        candidate=NS(parent=None,parent_type='OBJECT',constraints=[],rigid_body=None,animation_data=animation)
        self.assertTrue(transform_is_static(candidate))
        channelbag.fcurves=[curve('location',[0.,3.])]
        self.assertFalse(transform_is_static(candidate))


if __name__=='__main__':unittest.main()
