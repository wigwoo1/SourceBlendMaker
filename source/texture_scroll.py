"""Native UV animation for Source TextureScroll material proxies.

Formula follows Valve's texturescrollmaterialproxy.cpp. Model UVs have their
V coordinate flipped by SourceIO, so the T translation is inverted here.
"""
import math

def bake(meshes,assets,frames,seconds,curves_factory):
    from SourceIO.library.source1.vmt import VMT
    records=[];copies={}
    targets={'$basetexturetransform':'$basetexture','$bumptransform':'$bumpmap','$detailtexturetransform':'$detail'}
    for mesh in meshes:
        for slot in mesh.material_slots:
            material=slot.material
            if not material or not material.use_nodes or not material.get('full_path'):continue
            if material in copies:slot.material=copies[material];continue
            path=str(material['full_path']).replace('\\','/').removeprefix('materials/').removesuffix('.vmt')
            buffer=assets.buffer('materials/'+path+'.vmt')
            if buffer is None:continue
            vmt=VMT(buffer,assets.TinyPath('materials/'+path+'.vmt'),assets.cm)
            proxies=vmt.data.get('proxies') or {}
            scrolls=[proxy for name,proxy in proxies.items() if name.lower()=='texturescroll']
            if not scrolls:continue
            if not material.get('source_loaded'):
                from SourceIO.blender_bindings.material_loader.material_loader import ShaderRegistry
                ShaderRegistry.source1_create_nodes(assets.cm,material,vmt,{})
            original=material;material=material.copy();slot.material=material;copies[original]=material
            tree=material.node_tree
            for proxy in scrolls:
                target=str(proxy.get('texturescrollvar','')).lower()
                if target not in targets:
                    records.append({'material':path,'converted':False,'reason':'Unsupported TextureScroll target '+target});continue
                try:
                    def scalar(name,default):
                        value=proxy.get(name,default)
                        if isinstance(value,str) and value.startswith('$'):value=vmt.get_float(value,default)
                        result=float(value)
                        if not math.isfinite(result):raise ValueError('Nonfinite '+name)
                        return result
                    rate=scalar('texturescrollrate',1);angle=math.radians(scalar('texturescrollangle',0));scale=scalar('texturescale',1)
                    nodes=[node for node in tree.nodes if node.type=='TEX_IMAGE' and node.name.lower()==targets[target]]
                    if not nodes:raise ValueError('TextureScroll image node not found: '+targets[target])
                    for node in nodes:
                        uv=tree.nodes.new('ShaderNodeUVMap')
                        mapping=tree.nodes.new('ShaderNodeMapping');mapping.name='Source TextureScroll '+target
                        mapping.inputs['Scale'].default_value=(scale,scale,1)
                        tree.links.new(uv.outputs['UV'],mapping.inputs['Vector']);tree.links.new(mapping.outputs['Vector'],node.inputs['Vector'])
                        values=[(rate*math.cos(angle)*float(t),1-scale-rate*math.sin(angle)*float(t),0) for t in seconds]
                        mapping.inputs['Location'].default_value=values[0]
                        curves_factory(tree,material.name+' texture scroll',reuse=True).add(mapping.inputs['Location'].path_from_id('default_value'),frames,values)
                    records.append({'material':path,'converted':True,'target':target,'rate':rate,'angle_degrees':math.degrees(angle),'samples':len(frames),'source_time_phase_verified':False})
                except Exception as exc:records.append({'material':path,'converted':False,'reason':str(exc)})
    return records
