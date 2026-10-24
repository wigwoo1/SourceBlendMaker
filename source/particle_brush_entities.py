"""Static axis-aligned func_brush collision from translated BSP planes.

Solidity semantics follow Valve's src/game/server/modelentities.cpp.
Named/parented/rotated brushes require a separate entity-state evaluator.
"""
import math
import re
from bsp_collision import read_model_brushes


def vector(value):
    result=tuple(float(v) for v in str(value).split())
    if len(result)!=3 or not all(math.isfinite(v) for v in result):
        raise ValueError('Invalid brush entity vector')
    return result


def resolve(raw,entities,model_count):
    brushes=[];records=[];seen=set()
    for entity in entities:
        if entity.get('classname','').lower()!='func_brush':
            raise ValueError('Particle collision with this map model or brush entity is not implemented')
        model=entity.get('model','')
        if not re.fullmatch(r'\*[1-9][0-9]*',model):
            raise ValueError('Invalid func_brush model reference')
        index=int(model[1:])
        if index>=model_count or index in seen:raise ValueError('Invalid or repeated brush entity model')
        seen.add(index)
        if any(entity.get(k,'') for k in ('targetname','parentname','globalname','excludednpc')):
            raise ValueError('Named, parented or filtered brush collision requires entity-state evaluation')
        if vector(entity.get('angles','0 0 0'))!=(0.,0.,0.):
            raise ValueError('Rotated brush entity collision is not implemented')
        if float(entity.get('invert_exclusion',0))!=0 or float(entity.get('inputfilter',0))!=0:
            raise ValueError('Filtered brush entity collision is not implemented')
        flags=int(entity.get('spawnflags',0))
        if flags & ~2:raise ValueError('Unsupported brush entity spawn flags')
        solidity=int(entity.get('solidity',0));disabled=int(entity.get('startdisabled',0))
        if solidity not in (0,1,2) or disabled not in (0,1):raise ValueError('Invalid brush entity solidity')
        origin=vector(entity.get('origin','0 0 0'))
        solid=solidity!=1 and (solidity==2 or not disabled)
        selected=read_model_brushes(raw,index)['brushes']
        if solid:
            for brush in selected:
                sides=[{**s,'distance':s['distance']+sum(s['normal'][i]*origin[i] for i in range(3))}
                       for s in brush['sides']]
                brushes.append({**brush,'index':(index,brush['index']),'sides':sides})
        records.append({'model_index':index,'origin':origin,'solid':solid,
                        'brush_count':len(selected) if solid else 0,'solidity':solidity})
    if seen!=set(range(1,model_count)):
        raise ValueError('Unresolved BSP brush submodels remain')
    return brushes,records
