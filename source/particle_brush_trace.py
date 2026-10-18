"""Convex brush sweeps for collision development, in Source coordinates.

Uses an axis-aligned hull with particle radius as half extent. Engine collision
filters, displacement surfaces, model collision and Source epsilon parity remain
separate requirements; this helper does not enable particle collision baking.
"""
import math


def sweep(start,end,sides,radius=0.):
    start,end=tuple(map(float,start)),tuple(map(float,end))
    radius=float(radius)
    if len(start)!=3 or len(end)!=3 or not all(math.isfinite(v) for v in start+end+(radius,)) or radius<0:
        raise ValueError('Invalid brush trace segment or radius')
    if not sides:raise ValueError('Brush trace requires planes')
    enter,leave=0.,1.;normal=None;starts_inside=True;ends_inside=True
    for side in sides:
        n=tuple(map(float,side['normal']));distance=float(side['distance'])
        if len(n)!=3 or not all(math.isfinite(v) for v in n+(distance,)) or sum(v*v for v in n)<1e-12:
            raise ValueError('Invalid brush trace plane')
        # Minkowski expansion by an axis-aligned hull, including bevel planes.
        expanded=distance+radius*sum(abs(v) for v in n)
        a=sum(n[i]*start[i] for i in range(3))-expanded
        b=sum(n[i]*end[i] for i in range(3))-expanded
        starts_inside &= a<=0
        ends_inside &= b<=0
        if a>0 and b>0:return None
        if a<=0 and b<=0:continue
        fraction=a/(a-b)
        if a>b:
            if fraction>enter:enter,normal=fraction,n
        else:leave=min(leave,fraction)
        if enter>leave:return None
    if starts_inside:
        return {'fraction':0.,'start_solid':True,'all_solid':ends_inside,'normal':None}
    if 0<=enter<=leave and enter<=1:
        return {'fraction':enter,'start_solid':False,'all_solid':False,'normal':normal}
    return None


def trace_brushes(start,end,brushes,radius=0.,contents_mask=1):
    closest=None
    for brush in brushes:
        if not brush['contents']&contents_mask:continue
        hit=sweep(start,end,brush['sides'],radius)
        if hit is not None and (closest is None or hit['fraction']<closest['fraction']):
            closest={**hit,'brush_index':brush['index'],'contents':brush['contents']}
    return closest


class PreparedBrushTracer:
    """Validate static brush planes once; preserve the reference sweep math."""
    def __init__(self,brushes,contents_mask=1):
        self.brushes=[]
        for brush in brushes:
            if not brush['contents']&contents_mask:continue
            planes=[]
            for side in brush['sides']:
                n=tuple(map(float,side['normal']));d=float(side['distance'])
                if len(n)!=3 or not all(math.isfinite(v) for v in n+(d,)) or sum(v*v for v in n)<1e-12:
                    raise ValueError('Invalid prepared collision plane')
                planes.append((*n,d,sum(abs(v) for v in n)))
            if not planes:raise ValueError('Prepared brush requires planes')
            self.brushes.append((brush['index'],brush['contents'],planes))

    def __call__(self,start,end,radius=0.):
        start,end=tuple(map(float,start)),tuple(map(float,end));radius=float(radius)
        if len(start)!=3 or len(end)!=3 or not all(math.isfinite(v) for v in start+end+(radius,)) or radius<0:
            raise ValueError('Invalid prepared collision segment')
        closest=None
        for index,contents,planes in self.brushes:
            enter,leave=0.,1.;normal=None;inside=True;end_inside=True;miss=False
            for x,y,z,d,extent in planes:
                expanded=d+radius*extent
                a=x*start[0]+y*start[1]+z*start[2]-expanded
                b=x*end[0]+y*end[1]+z*end[2]-expanded
                inside &= a<=0;end_inside &= b<=0
                if a>0 and b>0:miss=True;break
                if a<=0 and b<=0:continue
                fraction=a/(a-b)
                if a>b:
                    if fraction>enter:enter,normal=fraction,(x,y,z)
                else:leave=min(leave,fraction)
                if enter>leave:miss=True;break
            if miss:continue
            hit={'fraction':0. if inside else enter,'start_solid':inside,
                 'all_solid':end_inside if inside else False,'normal':None if inside else normal,
                 'brush_index':index,'contents':contents}
            if closest is None or hit['fraction']<closest['fraction']:closest=hit
        return closest
