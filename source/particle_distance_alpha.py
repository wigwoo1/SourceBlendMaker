"""Installed SpriteCard distance alpha/outline without screen-space soft edges.

PS static 30720 supplies the equations; native Source image parity unverified.
"""
import math

ATTRIBUTE='sfm_particle_outline'

def settings(vmt):
    if not vmt.get_int('$distancealpha',0):return None
    if vmt.get_int('$softedges',0):raise ValueError('Distance-alpha screen-space soft edges require derivative support')
    if vmt.get_int('$dualsequence',0) or vmt.get_int('$splinetype',0):
        raise ValueError('Distance alpha with dual sequences or splines requires ordered shader integration')
    outline=bool(vmt.get_int('$outline',0))
    color,kind=vmt.get_vector('$outlinecolor',(1,1,1));color=list(color)[:3]
    if len(color)!=3:raise ValueError('Three outline color components required')
    if kind is int:color=[v/255 for v in color]
    alpha=vmt.get_float('$outlinealpha',0.)
    bounds=tuple(vmt.get_float(k,0.) for k in ('$outlinestart0','$outlinestart1','$outlineend0','$outlineend1'))
    if not all(math.isfinite(v) for v in (*color,alpha,*bounds)) or not 0<=alpha<=1:
        raise ValueError('Finite outline parameters required')
    if outline and not bounds[0]<bounds[1]<=bounds[2]<bounds[3]:
        raise ValueError('Ordered distinct outline transition bounds required')
    return dict(outline=outline,color=color,alpha=alpha,bounds=bounds,per_particle=bool(vmt.get_int('$perparticleoutline',0)))

def shader_color(rgb):
    if len(rgb)!=3 or not all(math.isfinite(v) and 0<=v<=1 for v in rgb):
        raise ValueError('Outline RGB must have three normalized channels')
    return tuple(v**2.2 for v in rgb)

def shade(texture,vertex,outline_color,per_particle_outline,bounds,overbright=1.):
    a=texture[3];s0,s1,e0,e1=bounds
    def smooth(start,end):
        t=min(1.,max(0.,(a-start)/(end-start)))
        return t*t*(3.-2.*t)
    factor=smooth(s0,s1) if a<=s1 else smooth(e1,e0)
    base=([texture[i]*vertex[i] for i in range(3)]+[a]) if a>=.5 else [0.,0.,0.,0.]
    if s0<=a<=e1:
        target=[outline_color[i]*per_particle_outline[i] for i in range(4)]
        base=[b+factor*(o-b) for b,o in zip(base,target)]
    return tuple([v*overbright for v in base[:3]]+[base[3]*vertex[3]])

def nodes(tree,color,alpha,config):
    """Return unpremultiplied RGB and opacity before ordinary vertex-alpha fade."""
    ns,ls=tree.nodes,tree.links
    def math_node(operation,*values):
        n=ns.new('ShaderNodeMath');n.operation=operation
        for socket,value in zip(n.inputs,values):
            if isinstance(value,(float,int)):socket.default_value=value
            else:ls.new(value,socket)
        return n.outputs[0]
    def mix(factor,a,b):
        n=ns.new('ShaderNodeMixRGB');n.blend_type='MIX'
        for socket,value in zip(n.inputs,(factor,a,b)):
            if isinstance(value,(tuple,list)):socket.default_value=(*value[:3],1.)
            elif isinstance(value,(float,int)):socket.default_value=value
            else:ls.new(value,socket)
        return n.outputs[0]
    body=math_node('SUBTRACT',1.,math_node('LESS_THAN',alpha,.5))
    base_color=mix(body,(0,0,0),color)
    base_alpha=math_node('MULTIPLY',alpha,body)
    if not config['outline']:return base_color,base_alpha
    s0,s1,e0,e1=config['bounds']
    def smooth(start,end):
        t=math_node('DIVIDE',math_node('SUBTRACT',alpha,start),end-start)
        t=math_node('MINIMUM',1.,math_node('MAXIMUM',0.,t))
        return math_node('MULTIPLY',math_node('MULTIPLY',t,t),math_node('SUBTRACT',3.,math_node('MULTIPLY',2.,t)))
    outer,inner=smooth(s0,s1),smooth(e1,e0)
    choose=math_node('GREATER_THAN',alpha,s1)
    factor=math_node('ADD',math_node('MULTIPLY',outer,math_node('SUBTRACT',1.,choose)),math_node('MULTIPLY',inner,choose))
    mask=math_node('MULTIPLY',math_node('SUBTRACT',1.,math_node('LESS_THAN',alpha,s0)),math_node('SUBTRACT',1.,math_node('GREATER_THAN',alpha,e1)))
    factor=math_node('MULTIPLY',factor,mask)
    outline_color=config['color'];outline_alpha=config['alpha']
    if config['per_particle']:
        attr=ns.new('ShaderNodeVertexColor');attr.layer_name=ATTRIBUTE
        tint=ns.new('ShaderNodeMixRGB');tint.blend_type='MULTIPLY';tint.inputs[0].default_value=1.
        tint.inputs[1].default_value=(*outline_color,1);ls.new(attr.outputs['Color'],tint.inputs[2])
        outline_color=tint.outputs[0]
        outline_alpha=math_node('MULTIPLY',outline_alpha,attr.outputs['Alpha'])
    result_color=mix(factor,base_color,outline_color)
    result_alpha=math_node('ADD',math_node('MULTIPLY',base_alpha,math_node('SUBTRACT',1.,factor)),math_node('MULTIPLY',outline_alpha,factor))
    return result_color,result_alpha
