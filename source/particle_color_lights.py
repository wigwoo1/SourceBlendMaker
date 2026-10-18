"""Static point-light particle colors from installed SFM LightDesc math.

Uses public Valve lightdesc/mathlib formulas; SSE reciprocal/rounding and
operator/tick ordering are approximate. Dynamic lights and normals reject.
"""
import math

def attenuation_coefficients(d50,d0):
    d50,d0=float(d50),float(d0)
    if not all(math.isfinite(v) for v in (d50,d0)) or d50<=0 or d0<=0:raise ValueError('Invalid particle light attenuation distances')
    if d0<d50:d0=2*d50
    a,b,c=0.,1.,0.
    if d0!=d50:
        for step in range(21):
            blend=step*.05;middle=2*(1-blend)+blend*(1+255*d50/d0)
            a=(255/d0-(middle-1)/d50)/(d0-d50)
            b=(middle-1)/d50-a*d50;c=1.
            if 2*a+b>=0:break
    normalization=2/(c+d50*(b+d50*a))
    return a*normalization,b*normalization,c*normalization

def settings(parameters):
    p=parameters;lights=[]
    if p.get('Compute Normals From Control Points',False):raise ValueError('Particle lighting normals are unverified')
    if any(float(p.get(k,0))!=0 for k in ('operator start fadein','operator end fadein','operator start fadeout','operator end fadeout','operator fade oscillate')):raise ValueError('Particle lighting strength fades are unverified')
    bias=float(p.get('Initial Color Bias',0))
    if not math.isfinite(bias):raise ValueError('Invalid particle initial color bias')
    for i in range(1,5):
        prefix=f'Light {i} '
        if int(p.get(prefix+'Type 0=Point 1=Spot',0))!=0:raise ValueError('Spot particle color lighting is unverified')
        if p.get(prefix+'Dynamic Light',False):raise ValueError('Dynamic particle color lighting is unverified')
        cp=float(p.get(prefix+'Control Point',0))
        if not math.isfinite(cp) or cp!=int(cp) or not 0<=cp<64:raise ValueError('Invalid particle light control point')
        offset=tuple(map(float,p.get(prefix+'Control Point Offset',(0,0,0))))
        color=tuple(map(float,p.get(prefix+'Color',(0,0,0,255))))
        if len(offset)!=3 or len(color)!=4 or not all(math.isfinite(v) for v in (*offset,*color)) or any(not 0<=v<=255 for v in color):raise ValueError('Invalid particle light offset or color')
        lights.append({'cp':int(cp),'offset':offset,'color':tuple(c/255 for c in color[:3]),'attenuation':attenuation_coefficients(p.get(prefix+'50% Distance',100),p.get(prefix+'0% Distance',200))})
    # Installed Operate at 0x1027727b copies light 3's LightDesc for light 4.
    # Its position still uses control point/offset 4.
    lights[3]['color']=lights[2]['color'];lights[3]['attenuation']=lights[2]['attenuation']
    return {'lights':lights,'bias':bias,'min_initial':bool(p.get('Clamp Minimum Light Value to Initial Color',False)),
            'max_initial':bool(p.get('Clamp Maximum Light Value to Initial Color',False))}

def color(config,center,initial,control_points):
    result=[float(c)*config['bias'] for c in initial]
    for light in config['lights']:
        if not any(light['color']):continue
        position=tuple(a+b for a,b in zip(control_points[light['cp']],light['offset']))
        distance_squared=max(1.,sum((a-b)**2 for a,b in zip(center,position)))
        a,b,c=light['attenuation'];denominator=c+b*math.sqrt(distance_squared)+a*distance_squared
        strength=1/max(1e-20,denominator)
        result=[old+strength*value for old,value in zip(result,light['color'])]
    low=initial if config['min_initial'] else (0,0,0)
    high=initial if config['max_initial'] else (1,1,1)
    return tuple(min(float(hi),max(float(lo),c)) for lo,hi,c in zip(low,high,result))
