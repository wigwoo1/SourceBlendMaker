import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from particle_spline import vertex,segment_knots,texture_coordinates,longitudinal_coordinates,mesh_geometry,shader_color

class SplineTests(unittest.TestCase):
    def test_installed_shader_color_power_from_shared_state(self):
        from particle_sprite_state import linear_color
        rgb=linear_color([81,97,255])
        actual=shader_color((*rgb,.37))
        for result,raw in zip(actual[:3],[81,97,255]):self.assertAlmostEqual(result,(raw/255)**2.2)
        self.assertEqual(actual[3],.37)
    def test_native_mesh_signed_width_and_authored_endpoint_fades(self):
        points=[(0,0,0,-2),(0,1,0,-2)]
        vertices,faces,uv,rgba=mesh_geometry(points,[(1,0,0,1),(0,0,1,.8)],2,(0,0,10),(0,1,2),radius_trail_fade=.5,alpha_trail_fade=.25,scale=1.)
        self.assertEqual(len(vertices),6);self.assertEqual(len(faces),2)
        self.assertAlmostEqual(__import__('math').dist(vertices[0],vertices[1]),2)
        self.assertAlmostEqual(__import__('math').dist(vertices[-2],vertices[-1]),1)
        self.assertEqual(rgba[0],(1,0,0,1))
        self.assertAlmostEqual(rgba[-1][3],.2)
        self.assertEqual(uv[-1],(1,2))
        self.assertEqual(mesh_geometry([],[],2,(0,0,10),()),([],[],[],[]))
        with self.assertRaises(ValueError):mesh_geometry(points,[(1,1,1,1)]*2,2,(0,0,10),(0,1))
    def test_cpu_longitudinal_coordinates_use_chord_and_scroll(self):
        values=longitudinal_coordinates([(0,0,0),(3,4,0),(3,4,2)],2,4,3,.5,64,128,.25)
        self.assertEqual(values,(2.25,12.25,22.25,26.25,30.25))
        for count in (0,-1,True,1.5):
            with self.assertRaises(ValueError):
                longitudinal_coordinates([(0,0,0),(1,0,0)],count,4,0,0,0,128)
    def test_shader_texture_coordinate_mapping(self):
        bounds=(.8,.2,.1,.9)
        self.assertEqual(texture_coordinates(bounds,0,0),(.1,.2))
        u,v=texture_coordinates(bounds,1,1)
        self.assertAlmostEqual(u,.8);self.assertAlmostEqual(v,.9)
        u,v=texture_coordinates(bounds,.5,.25)
        self.assertAlmostEqual(u,.275);self.assertAlmostEqual(v,.55)
        self.assertEqual(texture_coordinates((0,3,1,1),.5,1),(0,2))
    def test_endpoint_knots_preserve_signed_width(self):
        points=[(0,0,0,-100),(1,2,3,-150),(4,5,6,-220)]
        self.assertEqual(segment_knots(points,0),(( -1.,-2.,-3.,-50.),*points))
        self.assertEqual(segment_knots(points,1),(*points,(7.,8.,9.,-290.)))
        with self.assertRaises(ValueError):segment_knots(points,2)
    def test_signed_width_swaps_edges(self):
        knots=[(x,0,0,4) for x in (-1,0,1,2)]
        negative=[(*k[:3],-4) for k in knots]
        self.assertEqual(vertex(knots,.5,0,(0,0,10)),(.5,2.,0.))
        self.assertEqual(vertex(negative,.5,1,(0,0,10)),vertex(knots,.5,0,(0,0,10)))
    def test_width_uses_cubic_and_endpoint_scale(self):
        knots=[(-1,0,0,0),(0,0,0,2),(1,0,0,4),(2,0,0,0)]
        self.assertEqual(vertex(knots,0,0,(0,0,10)),(0.,1.,0.))
        self.assertEqual(vertex(knots,1,0,(0,0,10),.5),(1.,1.,0.))
        self.assertEqual(vertex(knots,.5,0,(0,0,10)),(.5,1.6875,0.))
