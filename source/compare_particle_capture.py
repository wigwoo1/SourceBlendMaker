"""Compare captured local particle inputs; not engine simulation equivalence."""
import math

def compare_particles(shot,captured,time,tolerance):
    pending=[shot.element.get('scene')];seen=set();systems={}
    while pending:
        element=pending.pop()
        if element is None or id(element) in seen:continue
        seen.add(id(element))
        if 'particleSystemType' in element:systems.setdefault(element.name,[]).append(element)
        pending.extend(element.get('children',[]))
    result={'checks':[],'mismatches':[],'missing':[],
            'scope':'Flags, simulation speed, random seed and local control-point positions/orientations plus scale when present; absent scales, ancestor transforms, lighting and particle simulation are not compared.',
            'uncompared_scales':[]}
    def record(system,attribute,actual,expected,control_index=None):
        try:
            a=list(actual) if isinstance(actual,(list,tuple)) else [actual]
            b=list(expected) if hasattr(expected,'__iter__') and not isinstance(expected,str) else [expected]
            if len(a)!=len(b):raise ValueError()
            a=[float(x) for x in a];b=[float(x) for x in b]
            if not a or not all(math.isfinite(x) for x in a+b):raise ValueError()
            if attribute=='orientation':
                if len(a)!=4:raise ValueError()
                def normalized(values):
                    largest=max(abs(x) for x in values)
                    if largest<=1e-12:raise ValueError()
                    scaled=[x/largest for x in values]
                    norm=math.sqrt(sum(x*x for x in scaled))
                    return [x/norm for x in scaled]
                a=normalized(a);b=normalized(b)
                # Quaternion signs are interchangeable; compare normalized rotations.
                difference=min(max(abs(x-y) for x,y in zip(a,b)),max(abs(x+y) for x,y in zip(a,b)))
            else:
                difference=max(abs(x-y) for x,y in zip(a,b))
        except (ValueError,TypeError):
            result['missing'].append({'system':system,'attribute':attribute,'control_index':control_index,'reason':'Missing, nonnumeric, or incompatible values'});return
        item={'system':system,'attribute':attribute,'control_index':control_index,
              'sfm_value':actual,'dmx_sample':list(expected) if hasattr(expected,'__iter__') and not isinstance(expected,str) else expected,'difference':difference}
        result['checks'].append(item)
        if difference>tolerance:result['mismatches'].append(item)
    for capture in captured:
        name=capture['name'];matches=systems.get(name,[])
        if len(matches)!=1:
            result['missing'].append({'system':name,'reason':'Particle identity missing or ambiguous'});continue
        system=matches[0]
        if str(system.get('particleSystemType'))!=str(capture.get('particleSystemType')):
            result['missing'].append({'system':name,'reason':'Particle type differs'});continue
        for attribute,default in (('visible',True),('simulating',True),('emitting',True),('simulationTimeScale',1.),('randomSeed',0)):
            record(name,attribute,capture.get(attribute),shot.value(system,attribute,time,system.get(attribute,default)))
        controls=system.get('controlPoints',[]);actual_controls=capture.get('control_points',[])
        if len(controls)!=len(actual_controls):
            result['missing'].append({'system':name,'reason':'Control-point count differs'});continue
        for index,(control,actual) in enumerate(zip(controls,actual_controls)):
            if control.name!=actual.get('name'):
                result['missing'].append({'system':name,'control_index':index,'reason':'Control-point identity differs'});continue
            record(name,'position',actual.get('position'),shot.value(control,'position',time,control.get('position')),index)
            record(name,'orientation',actual.get('orientation'),shot.value(control,'orientation',time,control.get('orientation')),index)
            expected_scale=shot.value(control,'scale',time,control.get('scale'))
            if actual.get('scale') is None and expected_scale is None:
                result['uncompared_scales'].append({'system':name,'control_index':index,'reason':'Neither capture nor saved element provides scale'})
            else:
                record(name,'scale',actual.get('scale'),expected_scale,index)
    result['all_compared_particle_inputs_match']=bool(result['checks']) and not result['missing'] and not result['mismatches']
    return result
