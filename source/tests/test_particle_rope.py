import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from particle_rope import ribbon,subdivide,settings

class RopeTests(unittest.TestCase):
    def test_installed_defaults_and_explicit_overrides(self):
        defaults=settings({})
        self.assertEqual(defaults['subdivision_count'],3)
        self.assertEqual(defaults['texel_size'],4.)
        explicit=settings({'subdivision_count':0,'texel_size':.002,'texture_offset':.75})
        self.assertEqual(explicit['subdivision_count'],0)
        self.assertEqual(explicit['texel_size'],.002)
        self.assertEqual(explicit['texture_offset'],.75)
    def test_unsupported_cp_texture_scaling_is_reported(self):
        for key in ('scale texture by CP distance','scale scroll by CP distance','scale offset by CP distance'):
            with self.assertRaises(ValueError):settings({key:True})
        with self.assertRaises(ValueError):settings({'texture_offset':float('nan')})
    def test_reversal_does_not_swap_ribbon_edges(self):
        vertices,faces,_,_=ribbon([(0,0,0),(1,0,0),(0,0,0)],[.1]*3,[(1,1,1,1)]*3,(0,0,1))
        self.assertEqual(len(faces),2)
        self.assertTrue(all(vertices[i][1]>0 for i in (0,2,4)))
    def test_invalid_geometry_inputs_are_reported(self):
        args=[[(0,0,0),(1,0,0)],[1,1],[(1,1,1,1)]*2,(0,0,1)]
        for change in ((0,[(float('nan'),0,0),(1,0,0)]),(2,[(1,1,float('inf'),1)]*2),(3,(0,0,0))):
            copy=list(args);copy[change[0]]=change[1]
            with self.assertRaises(ValueError):ribbon(*copy)
    def test_subdivision_preserves_knots_and_interpolates_attributes(self):
        points=[(0,0,0),(1,1,0),(2,0,0)];colors=[(1,0,0,1),(0,1,0,.5),(0,0,1,0)]
        p,w,c=subdivide(points,[1,2,3],colors,2)
        self.assertEqual(p[::2],points);self.assertEqual(w,[1,1.5,2,2.5,3])
        self.assertEqual(c[1],(.5,.5,0,.75));self.assertGreater(p[1][1],.5)
    def test_source_step_count(self):
        points=[(0,0,0),(1,1,0),(2,0,0)];colors=[(1,1,1,1)]*3
        self.assertEqual(subdivide(points,[1,2,3],colors,1),(points,[1,2,3],colors))
        self.assertEqual(len(subdivide(points,[1,2,3],colors,3)[0]),7)
    def test_disabled_and_invalid_subdivision(self):
        values=([(0,0,0)],[1],[(1,1,1,1)])
        self.assertEqual(subdivide(*values,0),values)
        for count in (-1,17,.5):
            with self.assertRaises(ValueError):subdivide(*values,count)
    def test_connected_width_color_and_scrolling_uv(self):
        colors=[(1,0,0,1),(0,1,0,.5),(0,0,1,0)]
        vertices,faces,uv,rgba=ribbon([(0,0,0),(1,0,0),(2,0,0)],[.1,.2,.3],colors,(0,0,1),2,.25)
        self.assertEqual(faces,[(0,1,3,2),(2,3,5,4)])
        self.assertAlmostEqual(abs(vertices[2][1]),.2)
        self.assertEqual(uv[0],(0,.25));self.assertEqual(uv[-1],(0,1.25))
        self.assertEqual(rgba[2],colors[1])
    def test_degenerate_segments_do_not_create_zero_area_faces(self):
        self.assertEqual(ribbon([(0,0,0)]*2,[1]*2,[(1,1,1,1)]*2,(0,0,1))[1],[])
