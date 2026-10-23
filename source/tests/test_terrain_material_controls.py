import unittest
from terrain_material_controls import neutral
from tile_emission import TILE


class VMT:
    shader='vertexlitgeneric'
    def __init__(self):
        self.values={'$zero':0.,'$detailblendfactor':0.,'$envmaptint':[0,0,0]}
        self.proxies=[]
        for prefix,matrix in (('$basetexture','$basetexturetransform'),('$detail','$detailtexturetransform')):
            self.values[matrix]='[1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1]'
            for i,axis in enumerate(('x','y')):
                self.proxies += [('add',{'srcvar1':prefix+'_scale_xy','srcvar2':'$zero','resultvar':prefix+f'_scale[{i}]'}),
                                 ('clamp',{'srcvar1':prefix+'_translate_'+axis,'min':0,'max':10,'resultvar':prefix+f'_translate[{i}]'})]
            self.proxies += [('texturetransform',{'scalevar':prefix+'_scale','rotatevar':prefix+'_rotate','translatevar':prefix+'_translate','resultvar':matrix})]
        self.proxies += [('clamp',{'srcvar1':'$envmap_color_'+axis,'min':0,'max':2,'resultvar':f'$envmaptint[{i}]'}) for i,axis in enumerate(('red','green','blue'))]
        class Proxies:
            def __init__(self,items):self.rows=items
            def items(self):return self.rows
        self.data={'proxies':Proxies(self.proxies)}
    def get_string(self,k,d=''):return self.values.get(k,d)
    def get_float(self,k,d=0):return float(self.values.get(k,d))
    def get_vector(self,k,d):return self.values.get(k,d),float


class Shot:
    def value(self,e,k,t,d):return e.get(k,d)


def controls():
    values={'$envmap':'cumulus_e','$detailblendfactor':0.}
    for prefix in ('$basetexture','$detail'):
        values.update({prefix+'_scale_xy':1.,prefix+'_rotate':0.,prefix+'_translate_x':0.,prefix+'_translate_y':0.})
    values.update({'$envmap_color_'+c:0. for c in ('red','green','blue')})
    return [{'mtlName':TILE,**{k:v}} for k,v in values.items()]


class TerrainNeutralTests(unittest.TestCase):
    def test_project_template_recognizes_thirteen_neutral_inputs(self):
        self.assertEqual(len(neutral(TILE,VMT(),controls(),Shot(),[0,1])),13)
    def test_other_materials_never_suppressed(self):
        self.assertFalse(neutral('models/other',VMT(),controls(),Shot(),[0]))
    def test_animated_transform_still_requires_support(self):
        class Animated(Shot):
            def value(self,e,k,t,d):return t if k=='$basetexture_rotate' else super().value(e,k,t,d)
        result=neutral(TILE,VMT(),controls(),Animated(),[0,1])
        self.assertNotIn('$basetexture_rotate',result)
    def test_nonblack_reflection_and_nonidentity_template_still_warn(self):
        vmt=VMT();vmt.values['$envmaptint']=[1,0,0]
        vmt.values['$detailtexturetransform']='[2 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1]'
        found=neutral(TILE,vmt,controls(),Shot(),[0])
        self.assertNotIn('$envmap',found);self.assertNotIn('$detail_scale_xy',found)
    def test_changed_proxy_binding_not_mistaken_for_identity(self):
        vmt=VMT();vmt.proxies[0][1]['srcvar1']='$other'
        self.assertNotIn('$basetexture_scale_xy',neutral(TILE,vmt,controls(),Shot(),[0]))
