"""Disabled prototype of the installed splinecard VS2.0 position calculation.

Observed endpoint generation is included; size fades and complete effect integration
remain pending. This module is not enabled in the production converter.
"""
import math

def shader_color(linear_rgba):
    """Decode splinecard's pow(raw vertex RGB, 2.2) from shared linear-sRGB state."""
    values=tuple(map(float,linear_rgba))
    if len(values)!=4 or not all(math.isfinite(v) for v in values) or any(v<0 for v in values[:3]):
        raise ValueError('Invalid spline color')
    raw=tuple(v*12.92 if v<=.0031308 else 1.055*v**(1/2.4)-.055 for v in values[:3])
    return (*(v**2.2 for v in raw),values[3])

def mesh_geometry(points,colors,subdivisions,eye,along,packed_bounds=(0,0,1,1),
                  radius_trail_fade=1.,alpha_trail_fade=1.,scale=.0254):
    """Build native mesh arrays for the decoded spline path; simulation is supplied.

    This does not make unsupported simulation operators eligible for conversion.
    """
    points=tuple(points);colors=tuple(tuple(c) for c in colors);along=tuple(along)
    if isinstance(subdivisions,bool) or not isinstance(subdivisions,int) or subdivisions<=0:
        raise ValueError('Positive integer subdivisions required')
    if len(colors)!=len(points) or any(len(c)!=4 or not all(math.isfinite(v) for v in c) for c in colors):
        raise ValueError('Finite RGBA required for every spline point')
    if not all(math.isfinite(v) for v in (alpha_trail_fade,radius_trail_fade,scale)) or scale<=0:
        raise ValueError('Invalid spline material multipliers or scale')
    if len(points)<2:return [],[],[],[]
    if len(along)!=(len(points)-1)*subdivisions+1:
        raise ValueError('Longitudinal coordinates must cover every subdivision')
    vertices=[];faces=[];uv=[];rgba=[]
    for index in range(len(points)-1):
        knots=segment_knots(points,index);begin=len(vertices)
        for step in range(subdivisions+1):
            for edge in (0,1):
                vertices.append(tuple(v*scale for v in vertex(knots,step/subdivisions,edge,eye,radius_trail_fade)))
        for step in range(subdivisions):
            faces.append((begin+2*step,begin+2*step+1,begin+2*step+3,begin+2*step+2))
            first=along[index*subdivisions+step];second=along[index*subdivisions+step+1]
            uv.extend(texture_coordinates(packed_bounds,value,edge) for value,edge in ((first,0),(first,1),(second,1),(second,0)))
            pair=[]
            for t in (step/subdivisions,(step+1)/subdivisions):
                color=tuple(a+(b-a)*t for a,b in zip(colors[index],colors[index+1]))
                pair.append((*color[:3],color[3]*(1+t*(alpha_trail_fade-1))))
            rgba.extend((pair[0],pair[0],pair[1],pair[1]))
    return vertices,faces,uv,rgba

def longitudinal_coordinates(points,subdivisions,texel_size,clock,scroll_rate,
                             texture_offset,mapping_dimension,context_offset=0.):
    """Observed unscaled CPU UV path, with explicitly supplied material dimension.

    Each knot chord contributes distance * texel_size, split evenly across its
    subdivisions. Source context changes, atlas bounds and Blender V convention
    still need integration; this is deliberately a disabled diagnostic helper.
    """
    points=tuple(tuple(map(float,p)) for p in points)
    if len(points)<2 or any(len(p)!=3 or not all(math.isfinite(v) for v in p) for p in points):
        raise ValueError('Finite xyz knots required')
    if isinstance(subdivisions,bool) or not isinstance(subdivisions,int) or subdivisions<=0:
        raise ValueError('Positive integer subdivisions required')
    if not all(math.isfinite(v) for v in (texel_size,clock,scroll_rate,texture_offset,mapping_dimension,context_offset)) or mapping_dimension<=0:
        raise ValueError('Invalid spline UV inputs')
    along=clock*scroll_rate+texture_offset/mapping_dimension+context_offset
    result=[along]
    for first,second in zip(points,points[1:]):
        increment=math.dist(first,second)*texel_size/subdivisions
        for _ in range(subdivisions):
            along+=increment
            result.append(along)
    return tuple(result)

def texture_coordinates(packed_bounds,along,edge):
    """Decoded oT0.xy for v6=(u_end,v_start,u_start,v_end).

    Caller must resolve Source CPU UV inputs and Blender texture V convention.
    """
    bounds=tuple(map(float,packed_bounds))
    if len(bounds)!=4 or not all(math.isfinite(v) for v in (*bounds,along,edge)):
        raise ValueError('Invalid spline texture coordinates')
    u_end,v_start,u_start,v_end=bounds
    return u_start+edge*(u_end-u_start),v_start+along*(v_end-v_start)

def segment_knots(points,index):
    """Prototype of the observed first/last xyz-width knot extrapolation."""
    values=tuple(tuple(map(float,p)) for p in points)
    if len(values)<2 or any(len(p)!=4 or not all(math.isfinite(v) for v in p) for p in values):
        raise ValueError('Spline points require finite xyz-width values')
    if isinstance(index,bool) or int(index)!=index or not 0<=index<len(values)-1:
        raise ValueError('Invalid spline segment')
    index=int(index)
    b=values[index];c=values[index+1]
    a=values[index-1] if index else tuple(2*x-y for x,y in zip(b,c))
    d=values[index+2] if index+2<len(values) else tuple(2*x-y for x,y in zip(c,b))
    return a,b,c,d

def vertex(knots,t,edge,eye,end_width_scale=1.):
    """Four xyz+signed-width knots; edge is the shader corner coordinate 0 or 1."""
    knots=tuple(tuple(map(float,k)) for k in knots);eye=tuple(map(float,eye))
    if len(knots)!=4 or any(len(k)!=4 for k in knots) or len(eye)!=3:
        raise ValueError('Spline needs four xyz-width knots and an eye position')
    if not all(math.isfinite(v) for k in knots for v in k) or not all(math.isfinite(v) for v in eye):
        raise ValueError('Invalid spline geometry')
    if not all(math.isfinite(v) for v in (t,edge,end_width_scale)) or not 0<=t<=1 or edge not in (0,1):
        raise ValueError('Invalid spline parameter')
    a,b,c,d=knots
    cubic=tuple(3*y-x-3*z+w for x,y,z,w in zip(a,b,c,d))
    quadratic=tuple(2*x-5*y+4*z-w for x,y,z,w in zip(a,b,c,d))
    linear=tuple(z-x for x,z in zip(a,c))
    center=tuple(y+.5*t*(l+t*(q+t*r)) for y,l,q,r in zip(b,linear,quadratic,cubic))
    tangent=tuple(.5*(l+2*t*q+3*t*t*r) for l,q,r in zip(linear,quadratic,cubic))[:3]
    view=tuple(p-e for p,e in zip(center[:3],eye))
    side=(view[1]*tangent[2]-view[2]*tangent[1],view[2]*tangent[0]-view[0]*tangent[2],view[0]*tangent[1]-view[1]*tangent[0])
    length=math.hypot(*side)
    if length<=1e-12:raise ValueError('Degenerate spline view or tangent')
    width=center[3]*(1+t*(end_width_scale-1))*(edge-.5)
    return tuple(p+s/length*width for p,s in zip(center[:3],side))
