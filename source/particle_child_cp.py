"""Position-only child CP writes inspected in installed SFM pet.dll.

Operate 0x102545d0 caps CPs to 0..63, reads active-buffer positions in
their existing order, and calls 0x100538b0, which also updates descendants.
The serialized Group ID is absent from this build's unpack table and unused
by Operate. Orientation is a separate branch and remains unsupported here.

The experimental parent bake binds this adapter through virtual CP views.
History's fixed clock is an explicit approximation; the caller supplies parent motion
and Source-compatible active-buffer ordering for engine parity.
"""
import bisect
import math


FUNCTION='Set child control points from particle positions'
_DEFAULTS={'operator start fadein':0.,'operator end fadein':0.,
    'operator start fadeout':0.,'operator end fadeout':0.,
    'operator fade oscillate':0.,'operator time offset seed':0,
    'operator time offset min':0.,'operator time offset max':0.,
    'operator time scale seed':0,'operator time scale min':1.,
    'operator time scale max':1.,'operator strength scale seed':0,
    'operator strength random scale min':1.,'operator strength random scale max':1.,
    'operator strength scale control point':-1,'operator end cap state':-1,
    'operator time strength random scale max':1.}


def _integer(value,label):
    if isinstance(value,bool):raise ValueError('Invalid '+label)
    try:number=float(value)
    except (TypeError,ValueError):raise ValueError('Invalid '+label) from None
    if not math.isfinite(number) or number!=int(number):raise ValueError('Invalid '+label)
    return int(number)


def settings(parameters):
    allowed={'functionName','operator enabled','operator help and notes',
        'Group ID to affect','First control point to set','# of control points to set',
        'first particle to copy','set orientation',*_DEFAULTS}
    unknown=set(parameters)-allowed
    if unknown:raise ValueError('Unverified child-control-point fields: '+', '.join(sorted(unknown)))
    for key,default in _DEFAULTS.items():
        try:value=float(parameters.get(key,default))
        except (TypeError,ValueError):raise ValueError('Invalid child-control-point '+key) from None
        if not math.isfinite(value) or value!=default:
            raise ValueError('Child-control-point timing/strength is not yet supported: '+key)
    if parameters.get('set orientation',False) not in (False,0):
        raise ValueError('Child-control-point orientation is not yet supported')
    first=max(0,min(63,_integer(parameters.get('First control point to set',0),'first control point')))
    count=max(0,min(64-first,_integer(parameters.get('# of control points to set',1),'control point count')))
    particle=_integer(parameters.get('first particle to copy',0),'first particle')
    if particle<0:raise ValueError('Negative first particle is not supported')
    return {'first_control_point':first,'count':count,'first_particle':particle,
        'set_orientation':False,
        'ignored_serialized_group_id':parameters.get('Group ID to affect',0)}


def updates(config,snapshot):
    """Map an immutable active-buffer snapshot into Source-unit CP positions."""
    start=config['first_particle']
    count=min(config['count'],max(0,len(snapshot.current)-start))
    return {config['first_control_point']+i:snapshot.current[start+i] for i in range(count)}


class History:
    """Sample CP writes chronologically and retain values after parent death.

    Backward queries read retained events and never resimulate in a different
    order. Unwritten CPs are absent so the caller can use the inherited CP.
    """
    def __init__(self,config,snapshot,step=1/120):
        if not math.isfinite(step) or step<=0:raise ValueError('Invalid child-control-point history step')
        self.config=dict(config);self.snapshot=snapshot;self.step=step
        self._tick=-1;self._events={}

    def query(self,clock):
        if not math.isfinite(clock) or clock<0:raise ValueError('Invalid child-control-point history clock')
        tick=math.floor(clock/self.step+1e-9)
        while self._tick<tick:
            current=self._tick+1
            snapshot=self.snapshot(current*self.step,self.step)
            for cp,position in updates(self.config,snapshot).items():
                events=self._events.setdefault(cp,[])
                if not events or events[-1][1]!=position:events.append((current,position))
            self._tick=current
        result={}
        for cp,events in self._events.items():
            index=bisect.bisect_right(events,tick,key=lambda item:item[0])-1
            if index>=0:result[cp]=events[index][1]
        return result
