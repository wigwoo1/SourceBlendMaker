import io,unittest
from types import SimpleNamespace
from unittest.mock import patch
from particle_tint_scene import prepare

class TintSceneTests(unittest.TestCase):
    def test_relative_map_and_integer_style_default(self):
        paths=[];settings=[]
        assets=SimpleNamespace(buffer=lambda p:(paths.append(p) or io.BytesIO(b'fixture')))
        scene=SimpleNamespace(objects=[],frame_current=1,frame_subframe=0)
        descriptor={'definitions':[{'instance_id':0,'parent_instance_id':None}],'control_points':[]}
        def query(raw,**kwargs):settings.append(kwargs);return lambda cp,p,t:(0,0,0,0)
        with patch('particle_tint_scene.MapTintQuery',query):
            provider,report=prepare(SimpleNamespace(map='stage_big',start=0),descriptor,scene,assets,24)
        self.assertEqual(paths,['maps/stage_big.bsp'])
        self.assertEqual(type(settings[0]['style_value']),int)
        self.assertEqual(settings[0]['style_value'],264)
        self.assertEqual(report['map'],'maps/stage_big.bsp')
        with self.assertRaisesRegex(ValueError,'control point unavailable'):
            provider(descriptor['definitions'][0],{'tint_perc':1},0,0)
    def test_invalid_map_never_reads_assets(self):
        def forbidden(path):raise AssertionError('Unsafe path reached asset resolver')
        for path in ('F:/maps/a.bsp','../a','/a','maps//a'):
            with self.assertRaises(ValueError):prepare(SimpleNamespace(map=path),{},None,SimpleNamespace(buffer=forbidden),24)
