import math,sys,tempfile,unittest
from pathlib import Path
sys.path[:0]=[str(Path(__file__).resolve().parents[1]),str(Path(__file__).resolve().parent)]
import test_particle_yaw_blender as fixture
bpy=fixture.bpy

@unittest.skipIf(bpy is None,"Run using Blender's Python")
class YawRampBakeTests(unittest.TestCase):
    def setUp(self):
        self.base=fixture.SpriteCardYawBakeTests();self.base.setUp()
    def bake(self,disabled=False,no_initializer=False):
        d=self.base.definition(yaw=0,roll=0)
        if no_initializer:d['modules']['initializers']=[m for m in d['modules']['initializers'] if m['function']!='Rotation Yaw Random']
        d['modules']['operators'].append({'function':'Ramp Scalar Linear Random','parameters':{'ramp field':12,
                  'ramp rate min':math.pi,'ramp rate max':math.pi,'operator enabled':not disabled}})
        records=self.base.bake(d)
        self.assertTrue(all(not r.get('reason') for r in records),records)
    def spans(self,frame):
        o=next(o for o in self.base.base.scene.objects if o.get('sfm_baked_frame')==frame)
        return tuple(max(v.co[i] for v in o.data.vertices)-min(v.co[i] for v in o.data.vertices) for i in range(3))
    def test_dynamic_yaw_rotates_sprite_in_depth_and_survives_save_reopen(self):
        self.bake()
        self.assertAlmostEqual(self.spans(1)[0],.2,places=5)
        x,y,z=self.spans(6)
        self.assertAlmostEqual(x,0.,places=5);self.assertAlmostEqual(y,.2,places=5);self.assertAlmostEqual(z,.2,places=5)
        name=self.base.base.scene.name
        with tempfile.TemporaryDirectory() as folder:
            path=str(Path(folder)/'yaw-ramp.blend')
            bpy.ops.wm.save_as_mainfile(filepath=path);bpy.ops.wm.open_mainfile(filepath=path)
            self.base.base.scene=bpy.data.scenes[name]
            self.assertAlmostEqual(self.spans(6)[2],.2,places=5)
    def test_disabled_ramp_keeps_original_geometry(self):
        self.bake(disabled=True)
        self.assertEqual(self.spans(1),self.spans(6))
    def test_ramp_works_from_default_yaw_without_initializer(self):
        self.bake(no_initializer=True)
        self.assertAlmostEqual(self.spans(6)[2],.2,places=5)

if __name__=='__main__':unittest.main(argv=[sys.argv[0]],verbosity=2)
