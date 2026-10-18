"""Camera-facing native ribbons; Source spline/UV conventions are unverified."""
import math

def settings(parameters):
    """Installed SFM rope unpack defaults; unsupported CP scaling is explicit."""
    result={'subdivision_count':3,'texel_size':4.,'texture_scroll_rate':0.,
            'texture_offset':0.,'scale CP start':-1,'scale CP end':-1,
            'scale texture by CP distance':False,'scale scroll by CP distance':False,
            'scale offset by CP distance':False,**parameters}
    if any(result[key] for key in ('scale texture by CP distance','scale scroll by CP distance','scale offset by CP distance')):
        raise ValueError('Rope texture scaling by control-point distance is unsupported')
    subdivisions=float(result['subdivision_count'])
    if not math.isfinite(subdivisions) or subdivisions!=int(subdivisions) or not 0<=subdivisions<=16:
        raise ValueError('Invalid rope subdivision count')
    for key in ('texel_size','texture_scroll_rate','texture_offset'):
        result[key]=float(result[key])
        if not math.isfinite(result[key]):raise ValueError('Invalid rope '+key)
    if result['texel_size']<=0:raise ValueError('Invalid rope texel size')
    result['subdivision_count']=int(subdivisions)
    return result

def subdivide(points,widths,colors,count):
    """Clamped Catmull-Rom positions with linear width/color interpolation."""
    if int(count)!=count or not 0<=count<=16:raise ValueError('Invalid rope subdivision count')
    if not (len(points)==len(widths)==len(colors)):raise ValueError('Rope attribute counts differ')
    if count==0 or len(points)<2:return points,widths,colors
    # Installed renderer allocates (point_count-1)*subdivision_count+1 knots.
    # A value of one keeps the original knots; zero retains the legacy bypass.
    output=[];sizes=[];rgba=[];steps=int(count)
    for i in range(len(points)-1):
        p0=points[max(0,i-1)];p1=points[i];p2=points[i+1];p3=points[min(len(points)-1,i+2)]
        for j in range(steps):
            t=j/steps
            output.append(tuple(.5*((2*b)+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t) for a,b,c,d in zip(p0,p1,p2,p3)))
            sizes.append(widths[i]+(widths[i+1]-widths[i])*t)
            rgba.append(tuple(a+(b-a)*t for a,b in zip(colors[i],colors[i+1])))
    return output+[points[-1]],sizes+[widths[-1]],rgba+[colors[-1]]

def ribbon(points,widths,colors,normal,texture_scale=1.,scroll=0.):
    if not (len(points)==len(widths)==len(colors)):raise ValueError('Rope attribute counts differ')
    if len(points)<2:return [],[],[],[]
    if not math.isfinite(texture_scale) or texture_scale<=0:raise ValueError('Invalid rope texture scale')
    def subtract(a,b):return tuple(x-y for x,y in zip(a,b))
    def length(v):return math.sqrt(sum(x*x for x in v))
    def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
    if len(normal)!=3 or not all(math.isfinite(v) for v in normal) or length(normal)<1e-10:raise ValueError('Invalid rope view normal')
    if not math.isfinite(scroll):raise ValueError('Invalid rope texture scroll')
    if any(len(p)!=3 or not all(math.isfinite(v) for v in p) for p in points):raise ValueError('Invalid rope position')
    if any(len(c)!=4 or not all(math.isfinite(v) for v in c) for c in colors):raise ValueError('Invalid rope color')
    vertices=[];distances=[0.];previous_side=None
    for i,(point,width) in enumerate(zip(points,widths)):
        if not math.isfinite(width) or width<0:raise ValueError('Invalid rope width')
        tangent=subtract(points[min(i+1,len(points)-1)],points[max(0,i-1)])
        side=cross(tangent,normal);size=length(side)
        if size<1e-10:
            side=previous_side or cross((1,0,0),normal);size=length(side)
            if size<1e-10:side=cross((0,1,0),normal);size=length(side)
        direction=tuple(v/size for v in side)
        if previous_side and sum(a*b for a,b in zip(direction,previous_side))<0:direction=tuple(-v for v in direction)
        previous_side=direction;side=tuple(v*width for v in direction)
        vertices.extend(tuple(p+sign*s for p,s in zip(point,side)) for sign in (-1,1))
        if i:distances.append(distances[-1]+length(subtract(point,points[i-1])))
    faces=[];uv=[];rgba=[]
    for i in range(len(points)-1):
        if length(subtract(points[i+1],points[i]))<1e-10:continue
        faces.append((2*i,2*i+1,2*i+3,2*i+2))
        a=distances[i]/texture_scale+scroll;b=distances[i+1]/texture_scale+scroll
        uv.extend(((0,a),(1,a),(1,b),(0,b)))
        rgba.extend((colors[i],colors[i],colors[i+1],colors[i+1]))
    return vertices,faces,uv,rgba
