import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from particle_texture_proxy import animations
class ProxyTests(unittest.TestCase):
    def test_default_and_case(self):
        supported,unsupported=animations({'AnimatedTexture':{'animatedTextureVar':'$normalmap','animatedTextureFrameNumVar':'$bumpframe'}})
        self.assertEqual(supported,[('$normalmap',15)]);self.assertEqual(unsupported,[])
    def test_unknown_and_malformed(self):
        for value in ('bad','nan','inf','0','-1'):
            supported,unsupported=animations({'AnimatedTexture':{'animatedtexturevar':'$normalmap','animatedtextureframenumvar':'$bumpframe','animatedtextureframerate':value}})
            self.assertEqual(supported,[]);self.assertEqual(unsupported,['AnimatedTexture'])
        self.assertEqual(animations({'AnimatedTexture':'bad','Other':{}})[1],['AnimatedTexture','Other'])
    def test_unsupported_mode_and_target(self):
        for extra in ({'animationnowrap':'1'},{'animatedtextureframenumvar':'$frame'},{'animatedtexturevar':'$basetexture'}):
            block={'animatedtexturevar':'$normalmap','animatedtextureframenumvar':'$bumpframe',**extra}
            self.assertEqual(animations({'AnimatedTexture':block})[0],[])
