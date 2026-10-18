import unittest
from particle_tint_provider import SceneTintProvider

class ProviderTests(unittest.TestCase):
    def test_source_units_cache_clock_and_parent_history(self):
        root={'instance_id':0,'parent_instance_id':None}
        child={'instance_id':1,'parent_instance_id':0}
        queries=[]
        def position(cp,time):return ((64 if time>=2 else 0)*.0254,0,0)
        def query(cp,point,time):queries.append((cp,point,time));return (32 if time<2 else 224,64,128,0)
        provider=SceneTintProvider([root,child],position,query,context_position=(0,0,0))
        p={'tint_perc':1}
        provider(root,p,1,1);provider(root,p,2,2)
        self.assertEqual(provider(child,p,.5,.5)[0],32)
        self.assertEqual(provider(child,p,1.5,1.5)[0],32)
        self.assertEqual(provider(child,p,2.5,2.5)[0],224)
        self.assertEqual(queries[1],(0,(64.,0.,0.),2))
        self.assertEqual(len(queries),3)
        self.assertEqual(len(provider.parent_reads),2)
    def test_cache_refresh_uses_current_query_time(self):
        root={'instance_id':0,'parent_instance_id':None};times=[]
        def query(cp,p,t):times.append(t);return (int(t),0,0,0)
        provider=SceneTintProvider([root],lambda cp,t:(t,0,0),query,scale=1,context_position=(0,0,0))
        parameters={'tint_perc':1,'tint update movement threshold':0}
        self.assertEqual(provider(root,parameters,1,1)[0],1)
        self.assertEqual(provider(root,parameters,2,2)[0],2)
        self.assertEqual(times,[1,2])
        with self.assertRaises(ValueError):provider(root,parameters,1.5,1.5)
    def test_multiple_renderer_passes_share_identical_tint_state(self):
        definition={'instance_id':4,'parent_instance_id':None}
        queries=[]
        provider=SceneTintProvider([definition],lambda cp,t:(0,0,0),
            lambda cp,p,t:(queries.append((cp,p,t)) or (90,120,210,0)),
            scale=1,context_position=(0,0,0))
        pass_zero={**definition,'renderer_pass_index':0,'renderer_pass_count':2}
        pass_one={**definition,'renderer_pass_index':1,'renderer_pass_count':2}
        parameters={'tint_perc':1,'tint update movement threshold':32}
        self.assertEqual(provider(pass_zero,parameters,1,1),(90,120,210,0))
        self.assertEqual(provider(pass_one,parameters,1,1),(90,120,210,0))
        self.assertEqual(len(queries),1)
        self.assertEqual(provider.histories[4].times,[1,1])
    def test_invalid_graphs_rejected(self):
        for graph in ([{'instance_id':0,'parent_instance_id':0}],
                      [{'instance_id':0,'parent_instance_id':3}],
                      [{'instance_id':0},{'instance_id':0}]):
            with self.assertRaises(ValueError):SceneTintProvider(graph,lambda cp,t:(0,0,0),lambda cp,p,t:(0,0,0,0),context_position=(0,0,0))
