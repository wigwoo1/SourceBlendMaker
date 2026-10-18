"""Replace complete numbered image sequences with packed native texture selectors."""
import re
from pathlib import Path

def pack_sequences(use_source_rate=False):
 import bpy
 from texture_switch import switch_images
 trees={tree for owner in [*bpy.data.materials,*bpy.data.worlds] if (tree:=owner.node_tree) is not None}
 trees.update(tree for tree in bpy.data.node_groups if tree.bl_idname=='ShaderNodeTree')
 records=[];cache={}
 for tree in trees:
  for node in list(tree.nodes):
   image=getattr(node,'image',None)
   if node.type!='TEX_IMAGE' or image is None or image.source!='SEQUENCE':continue
   user=node.image_user
   if not user.use_auto_refresh:
    records.append({'image':image.name,'packed':False,'reason':'Manual sequence refresh is not supported'});continue
   source=Path(bpy.path.abspath(image.filepath));match=re.match(r'^(.*?)(\d+)$',source.stem)
   count=user.frame_duration
   if not match or count<1:
    records.append({'image':image.name,'packed':False,'reason':'Sequence has no numbered frame path'});continue
   prefix,digits=match.groups();start=user.frame_start;offset=user.frame_offset;cyclic=user.use_cyclic
   # Blender resolves absolute numbered files; the filepath's number is only
   # a naming template. Its offset is applied after clamping / cycling.
   first=1+offset if cyclic else offset
   numbers=range(first,count+offset+1)
   paths=[source.with_name(prefix+str(number).zfill(len(digits))+source.suffix) for number in numbers]
   if any(not path.is_file() for path in paths):
    records.append({'image':image.name,'packed':False,'reason':'Numbered sequence frames are missing'});continue
   cache_key=(str(source),tuple(numbers),image.colorspace_settings.name,image.alpha_mode)
   images=cache.get(cache_key)
   if images is None:
    images=[]
    for path in paths:
     frame=bpy.data.images.load(str(path),check_existing=False)
     frame.colorspace_settings.name=image.colorspace_settings.name;frame.alpha_mode=image.alpha_mode
     frame.pack();frame.filepath='//textures/'+path.name;images.append(frame)
    cache[cache_key]=images
   raw=f'(floor(frame)-{start})'
   rate=float(node.get('source_frame_rate',0)) if use_source_rate else 0.
   fps=bpy.context.scene.render.fps/bpy.context.scene.render.fps_base
   if rate>0:
    raw=f'floor((frame-{start})*{rate/fps:.12g})'
   choice=f'({raw}%{count})' if cyclic else f'min(max({raw}+1,0),{count})'
   def factor(socket,index):
    driver=socket.driver_add('default_value').driver
    driver.type='SCRIPTED';driver.expression=f'1.0 if {choice}=={index} else 0.0'
   original_name=image.name;node.image=images[0]
   switch_images(tree,node,images,None,None,None,factor_callback=factor)
   records.append({'image':original_name,'tree':tree.name,'node':node.name,'packed':True,'frames':count,'frame_start':start,'frame_offset':offset,'cyclic':cyclic,'source_frame_rate':rate,'scene_fps':fps,'source_proxy_phase_verified':False if rate>0 else None})
 return records
