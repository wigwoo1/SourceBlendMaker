"""Native Sprite shader mode checks using an actual mounted VTF."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import bpy
from blender_worker import Assets
from particles import sprite_material,material_failure
from SourceIO.library.utils import MemoryBuffer
from SourceIO.blender_bindings.bindings import register
register()

assets=Assets({'sfm':'D:/SteamLibrary/steamapps/common/SourceFilmmaker','output':str(Path('work/sprite-mode-test.blend').resolve())})
original=assets.buffer
mode=1;ignore=1
def buffer(path):
    if str(path)=='materials/diagnostic/sprite.vmt':
        return MemoryBuffer(('"Sprite" { "$basetexture" "effects/electro_beam" "$spriterendermode" "'+str(mode)+'" "$ignorevertexcolors" "'+str(ignore)+'" }').encode())
    return original(path)
assets.buffer=buffer
checks=[]
for mode,ignore in ((1,1),(2,1),(4,1),(5,1),(5,0)):
    material=sprite_material(assets,'diagnostic/sprite.vmt')
    nodes=material.node_tree.nodes
    output=next(n for n in nodes if n.type=='OUTPUT_MATERIAL')
    blend=output.inputs['Surface'].links[0].from_node
    assert blend.type==('ADD_SHADER' if mode==5 else 'MIX_SHADER')
    vertex=next(n for n in nodes if n.type=='VERTEX_COLOR')
    used=any(link.from_node==vertex for link in material.node_tree.links)
    assert used==(mode!=5 or ignore==0),(mode,ignore,used)
    assert any(n.type=='TEX_IMAGE' and n.image and n.image.packed_file for n in nodes)
    checks.append({'mode':mode,'ignore_vertex_colors':ignore,'blend':blend.type,'vertex_colors_used':used})
mode=7
try:sprite_material(assets,'diagnostic/sprite.vmt')
except ValueError as exc:
    assert material_failure('diagnostic/sprite.vmt',exc)['failure_category']=='unsupported_material'
else:raise AssertionError('Unimplemented frame blending must be reported')
Path('outputs/particle_sprite_mode_validation.json').write_text(json.dumps({'checks':checks,'unsupported_mode_reported':True},indent=2))
print('SPRITE MODE CHECKS PASSED')
