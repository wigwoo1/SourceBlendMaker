import unittest
from particle_brush_trace import sweep,trace_brushes,PreparedBrushTracer

def box(low,high):
    sides=[]
    for axis in range(3):
        for sign,value in ((1,high[axis]),(-1,-low[axis])):
            normal=[0,0,0];normal[axis]=sign
            sides.append({'normal':normal,'distance':value})
    return sides

class BrushTraceTests(unittest.TestCase):
    def test_thin_surface_crossed_between_samples(self):
        hit=sweep((0,0,10),(0,0,-10),box((-5,-5,-.1),(5,5,.1)))
        self.assertAlmostEqual(hit['fraction'],.495)
        self.assertEqual(hit['normal'],(0,0,1))
    def test_radius_hits_before_center_and_parallel_miss(self):
        sides=box((-1,-1,-1),(1,1,1))
        self.assertAlmostEqual(sweep((-5,0,0),(5,0,0),sides,1)['fraction'],.3)
        self.assertIsNone(sweep((-5,3,0),(5,3,0),sides,1))
    def test_initial_inside_and_exit(self):
        sides=box((-1,-1,-1),(1,1,1))
        self.assertTrue(sweep((0,0,0),(.5,0,0),sides)['all_solid'])
        hit=sweep((0,0,0),(5,0,0),sides)
        self.assertTrue(hit['start_solid']);self.assertFalse(hit['all_solid'])
    def test_mask_and_nearest_brush(self):
        brushes=[{'index':0,'contents':1,'sides':box((3,-1,-1),(4,1,1))},
                 {'index':1,'contents':32,'sides':box((0,-1,-1),(1,1,1))},
                 {'index':2,'contents':1,'sides':box((1,-1,-1),(2,1,1))}]
        self.assertEqual(trace_brushes((-5,0,0),(5,0,0),brushes)['brush_index'],2)
        self.assertEqual(trace_brushes((-5,0,0),(5,0,0),brushes,contents_mask=32)['brush_index'],1)
    def test_prepared_matches_reference_across_seeded_segments(self):
        import random
        rng=random.Random(817)
        brushes=[{'index':0,'contents':1,'sides':box((-1,-2,-3),(1,2,3))},
                 {'index':1,'contents':1,'sides':box((3,-1,-1),(4,1,1))}]
        prepared=PreparedBrushTracer(brushes)
        for _ in range(200):
            a=[rng.uniform(-6,6) for _ in range(3)];b=[rng.uniform(-6,6) for _ in range(3)];r=rng.random()
            self.assertEqual(prepared(a,b,r),trace_brushes(a,b,brushes,r))
