"""Bake supported ordered VMT color proxies from session material controls."""
import re


class ColorOverride(dict):
    name='baked material color proxies'


def prepare(gm,shot,seconds,assets):
    overrides=list(gm.get('materials') or [])
    if assets is None:return overrides,shot,[],set()
    from SourceIO.library.source1.vmt import VMT
    groups={};records=[];consumed=set()
    for override in overrides:
        path=str(override.get('mtlName','')).replace('\\','/').lower().removeprefix('materials/').removesuffix('.vmt')
        groups.setdefault(path,[]).append(override)
    for path,controls in groups.items():
        keys={key.lower() for control in controls for key in control if key.startswith('$')}
        if not any('color_' in key for key in keys):continue
        buffer=assets.buffer('materials/'+path+'.vmt')
        if buffer is None:continue
        vmt=VMT(buffer,assets.TinyPath('materials/'+path+'.vmt'),assets.cm)
        from terrain_material_controls import neutral
        neutral_keys=neutral(path,vmt,controls,shot,seconds)
        consumed.update((path,key) for key in neutral_keys)
        if neutral_keys:
            records.append({'material':path,'neutral_controls':sorted(neutral_keys),
                            'samples':len(seconds),'reason':'Identity texture transforms or disabled detail/reflection contribution on terrain-plane template'})
        proxies=vmt.data.get('proxies')
        if proxies is None:continue
        operations=[]
        for kind,proxy in proxies.items():
            if not hasattr(proxy,'get'):continue
            target=str(proxy.get('resultvar','')).lower()
            match=re.fullmatch(r'(\$color2?)\[([012])\]',target)
            if kind.lower()!='clamp' or not match:continue
            source=str(proxy.get('srcvar1','')).lower()
            if source not in keys:continue
            operations.append((match.group(1),int(match.group(2)),source,float(proxy.get('min',0)),float(proxy.get('max',1))))
        if not operations:continue
        for output in dict.fromkeys(op[0] for op in operations):
            selected=[op[1:] for op in operations if op[0]==output]
            values=[];base,value_type=vmt.get_vector(output,[1,1,1])
            base=[float(component)/(255 if value_type is int else 1) for component in base]
            if len(base)==1:base*=3
            base=(base+[1,1,1])[:3]
            for time in seconds:
                inputs={key.lower():shot.value(control,key,time,control[key])
                        for control in controls for key in control if key.startswith('$')}
                color=list(base)
                authored=inputs.get(output)
                if isinstance(authored,(list,tuple)):
                    color=(list(authored)+[1,1,1])[:3]
                for component,source,minimum,maximum in selected:
                    color[component]=max(minimum,min(maximum,float(inputs[source])))
                values.append(color)
            synthetic=ColorOverride(mtlName=path,**{output:values[0]})
            synthetic.proxy_output=output
            synthetic.proxy_samples=dict(zip(seconds,values));overrides.append(synthetic)
            consumed.update((path,source) for _,source,_,_ in selected)
            records.append({'material':path,'output':output,'inputs':[source for _,source,_,_ in selected],
                            'samples':len(values),'first_color':values[0]})
    class SampledShot:
        def value(self,element,key,time,default=None):
            if isinstance(element,ColorOverride) and key==element.proxy_output:return element.proxy_samples[time]
            return shot.value(element,key,time,default)
    return overrides,SampledShot(),records,consumed
