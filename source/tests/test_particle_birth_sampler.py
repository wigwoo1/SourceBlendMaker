import unittest
from types import SimpleNamespace
from particle_birth_sampler import bind
from unittest.mock import patch


class BirthSamplerTests(unittest.TestCase):
    def sampler(self,states,definition,**extra):
        arguments=dict(states=states,plane_force_configs=[],experimental_pull=False,
            pull_modules=[],ordered_spatial=False,twist_modules=[],definition=definition,
            positions={},scale=1,record={},plane_histories={},
            evaluate=lambda d,s,a,l,scale:(s['offset'],d['color'],1,0),
            planned_definition=definition,Vector=tuple,model_context=None,
            set_time=None,descriptor={},control_objects={},fps=60,shot=None,
            prepared_clock=None,pull_target_cache={},scene=None,segments=[])
        arguments.update(extra)
        return bind(**arguments)

    def test_ordered_force_branch_has_its_required_definition_helpers(self):
        definition={'color':'red','modules':{'forces':[{'function':'twist around axis','parameters':{}}]}}
        states={0:{'offset':(1,2,3)}}
        sampler=self.sampler(states,definition,ordered_spatial=True,
            twist_modules=[{}],positions={0:(0,0,0)})
        with patch('particle_spatial_force_context.bind',return_value='bound') as binding:
            sampler(SimpleNamespace(index=0,simulation_time=.5),0,1)
        self.assertEqual(binding.call_args.args[0],definition['modules']['forces'])
        self.assertEqual(states[0]['_spatial_acceleration'],'bound')

    def test_later_definition_does_not_replace_retained_sampler_state(self):
        states={0:{'offset':(1,2,3)}};definition={'color':'red'}
        first=self.sampler(states,definition)
        states={0:{'offset':(4,5,6)}};definition={'color':'blue'}
        second=self.sampler(states,definition)
        birth=SimpleNamespace(index=0,simulation_time=.5)
        self.assertEqual(first(birth,0,1)[:2],((1,2,3),'red'))
        self.assertEqual(second(birth,0,1)[:2],((4,5,6),'blue'))
