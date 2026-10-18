"""SFM session graph, timing and animation sampling (no Blender dependency)."""
from __future__ import annotations
import ast
import bisect
import math
from pathlib import Path
import datamodel


def eid(element):
    return str(element.id) if element is not None else None


def kind(element, name):
    return element is not None and element.type.lstrip('C') == name


def shot_frame_count(shot, fps, following=None):
    count=max(1,math.ceil(shot.duration*fps))
    if following is not None and abs(following.start-(shot.start+shot.duration))<=1e-4:
        boundary=round(following.start*fps)-round(shot.start*fps)
        if boundary>0:count=min(count,boundary)
    return count


class Clock:
    """Global seconds = origin + local seconds * rate."""
    def __init__(self, origin=0., rate=1.):
        self.origin, self.rate = origin, rate

    def child(self, clip):
        tf = clip.get('timeFrame') or {}
        scale = float(tf.get('scale', 1.))
        if abs(scale) < 1e-10:
            raise ValueError(f'Zero time scale on {clip.name}')
        return Clock(self.origin + self.rate * (float(tf.get('start', 0.)) - float(tf.get('offset', 0.)) / scale), self.rate / scale)

    def global_time(self, local):
        return self.origin + float(local) * self.rate

    def local_time(self, global_seconds):
        return (global_seconds - self.origin) / self.rate


def clip_children(clip):
    groups = list(clip.get('trackGroups', []))
    sub = clip.get('subClipTrackGroup')
    if sub is not None:
        groups.append(sub)
    for group in groups:
        if group.get('mute', False):
            continue
        for track in group.get('tracks', []):
            if not track.get('mute', False):
                yield from track.get('children', [])


def quat_slerp(a, b, f):
    dot = sum(x*y for x,y in zip(a,b))
    if dot < 0:
        b, dot = [-v for v in b], -dot
    dot = max(-1., min(1., dot))
    if dot > .9995:
        out = [x+(y-x)*f for x,y in zip(a,b)]
    else:
        angle = math.acos(dot)
        out = [(x*math.sin((1-f)*angle)+y*math.sin(f*angle))/math.sin(angle) for x,y in zip(a,b)]
    length = math.sqrt(sum(x*x for x in out))
    return [x/length for x in out] if length else [0,0,0,1]


def iter_shifted(values):
    iterator=iter(values);next(iterator,None)
    return iterator


class CurveTypes:
    def __init__(self,types,default,count):self.types,self.default,self.count=types,default,count
    def __len__(self):return self.count
    def __getitem__(self,index):
        if not 0<=index<self.count:raise IndexError(index)
        return (int(self.types[index]) or self.default) if index<len(self.types) else self.default
    def __iter__(self):return (self[i] for i in range(self.count))


class Curve:
    def __init__(self, channel, clock):
        self.channel, self.clock = channel, clock
        self.layers = []
        self.layer_curves = []
        self.issues = []
        log = channel.get('log')
        if log is not None:
            info=log.get('curveinfo') or {}
            default_curve=int(info.get('defaultCurveType',info.get('defaultcurvetype',0)))
            for layer in log.get('layers', []):
                times, values = layer.get('times', []), layer.get('values', [])
                if layer.get('compressed'):
                    self.issues.append('Compressed animation layer requires decompression')
                curve_types=layer.get('curvetypes',[])
                resolved=CurveTypes(curve_types,default_curve,len(times))
                if any(x not in (0,1542,3855) for x in (resolved if curve_types else [default_curve])):
                    self.issues.append('Nonlinear SFM curve sampled with linear interpolation')
                if len(times) != len(values):
                    self.issues.append('Mismatched animation times and values')
                ordered=all(a<=b for a,b in zip(times,iter_shifted(times)))
                if times and len(times)==len(values) and ordered:
                    self.layers.append((times,values));self.layer_curves.append(resolved)
                else:
                    pairs = sorted(((float(t),v,resolved[i]) for i,(t,v) in enumerate(zip(times,values))),key=lambda p:p[0])
                    if pairs:
                        self.layers.append(([p[0] for p in pairs], [p[1] for p in pairs]))
                        self.layer_curves.append([p[2] for p in pairs])
        if len(self.layers) > 1:
            self.issues.append('Multiple SFM log layers: top layer takes precedence')

    def sample(self, seconds):
        if not self.layers:
            source = self.channel.get('fromElement')
            return source.get(self.channel.get('fromAttribute')) if source is not None else None
        t = self.clock.local_time(seconds)
        times, values = self.layers[-1]
        i = bisect.bisect_right(times, t)
        if not i:
            return values[0]
        if i == len(times):
            return values[-1]
        a,b = values[i-1], values[i]
        # Valve packs inbound/outbound interpolation types into two bytes;
        # 0x0f0f is HOLD on both sides, 0x0606 is explicit LINEAR.
        if self.layer_curves[-1][i-1]==3855:return a
        f = (t-times[i-1]) / (times[i]-times[i-1])
        if isinstance(a, (bool, str, int)):
            return a
        if isinstance(a, datamodel.Quaternion):
            return quat_slerp(a,b,f)
        if isinstance(a, (list, tuple)):
            return [x+(y-x)*f for x,y in zip(a,b)]
        return a+(b-a)*f


def expression(expr, values):
    """Evaluate only a small numeric expression language, never Python code."""
    functions = {'lerp':lambda x,a,b:a+(b-a)*x, 'min':min, 'max':max,
                 'clamp':lambda x,a,b:max(a,min(b,x)), 'abs':abs,
                 'sin':math.sin, 'cos':math.cos, 'sqrt':math.sqrt, 'pow':pow,
                 'floor':math.floor}
    def visit(n):
        if isinstance(n, ast.Expression): return visit(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value,(int,float)): return n.value
        if isinstance(n, ast.Name): return float(values.get(n.id,0))
        if isinstance(n, ast.UnaryOp) and isinstance(n.op,(ast.UAdd,ast.USub)):
            return visit(n.operand) * (-1 if isinstance(n.op,ast.USub) else 1)
        if isinstance(n, ast.BinOp):
            a,b = visit(n.left),visit(n.right)
            if isinstance(n.op,ast.Add):return a+b
            if isinstance(n.op,ast.Sub):return a-b
            if isinstance(n.op,ast.Mult):return a*b
            if isinstance(n.op,ast.Div):return a/b if b else 0.
            if isinstance(n.op,ast.Pow):return a**b
        if isinstance(n, ast.Call) and isinstance(n.func,ast.Name) and n.func.id in functions and not n.keywords:
            return functions[n.func.id](*[visit(x) for x in n.args])
        raise ValueError(f'Unsupported SFM expression: {expr}')
    return visit(ast.parse(expr,mode='eval'))


class Shot:
    def __init__(self, element, clock, parent_clock, default_map):
        self.element,self.clock = element,clock
        tf = element.get('timeFrame') or {}
        self.start = parent_clock.global_time(tf.get('start',0))
        self.duration = float(tf.get('duration',0))*abs(parent_clock.rate)
        self.map = element.get('mapname') or default_map
        self.curves = {}
        self.issues = []
        self.sounds = []
        def walk(clip, parent):
            for child in clip_children(clip):
                if child.get('mute',False): continue
                child_clock=parent.child(child)
                if kind(child,'DmeChannelsClip'):
                    for ch in child.get('channels',[]):
                        target=ch.get('toElement')
                        if target is not None:
                            curve=Curve(ch,child_clock)
                            self.curves[(eid(target),ch.get('toAttribute'),int(ch.get('toIndex',0)))]=curve
                            self.issues.extend(f'{ch.name}: {x}' for x in curve.issues)
                elif kind(child,'DmeSoundClip'):
                    self.sounds.append((child,child_clock))
                if not kind(child,'DmeFilmClip'):walk(child,child_clock)
        walk(element,clock)
        self.connections={}
        for animset in element.get('animationSets',[]):
            for operator in animset.get('operators',[]):
                if not kind(operator,'DmeConnectionOperator'):continue
                source=operator.get('input')
                if source is None:continue
                for output in operator.get('outputs',[]):
                    target=output.get('element')
                    if target is not None:
                        self.connections[(eid(target),output.get('attribute'),int(output.get('index',0)))]=source

    def is_constant(self,element,attribute,index=0):
        """Conservative proof for direct attributes and recorded log values."""
        if element is None:return True
        key=(eid(element),attribute,index)
        if key in self.connections:return False
        curve=self.curves.get(key)
        if curve is None or int(curve.channel.get('mode',3))==0:
            return not kind(element,'DmeExpressionOperator')
        if int(curve.channel.get('mode',3))!=3 or not curve.layers:return False
        values=curve.layers[-1][1]
        first=values[0]
        # Slerp normalizes quaternions between keys. Even identical stored
        # endpoints can produce a slightly different normalized value, so
        # retain full sampling for these recorded rotations.
        if isinstance(first,datamodel.Quaternion) and len(values)>1:return False
        if isinstance(first,(list,tuple)):
            first=tuple(first)
            return all(tuple(value)==first for value in values)
        return all(value==first for value in values)

    def value(self, element, attribute, seconds, default=None, index=0, _seen=None):
        if element is None:return default
        _seen=set() if _seen is None else _seen
        key=(eid(element),attribute,index)
        if key in _seen:return element.get(attribute,default)
        _seen=_seen|{key}
        curve=self.curves.get((eid(element),attribute,index))
        if curve and int(curve.channel.get('mode',3))!=0:
            mode=int(curve.channel.get('mode',3))
            if curve.layers and mode==3:value=curve.sample(seconds)
            else:
                ch=curve.channel
                value=self.value(ch.get('fromElement'),ch.get('fromAttribute'),seconds,default,int(ch.get('fromIndex',0)),_seen)
            if value is not None:return value
        connection=self.connections.get(key)
        if connection is not None:
            return self.value(connection.get('element'),connection.get('attribute'),seconds,default,
                              int(connection.get('index',0)),_seen)
        if kind(element,'DmeExpressionOperator') and attribute=='result':
            vals={k:self.value(element,k,seconds,v,_seen=_seen) for k,v in element.items() if isinstance(v,(int,float)) and k!='result'}
            return expression(element.get('expr','0'),vals)
        if kind(element,'DmePackColorOperator') and attribute=='color':
            return [255*self.value(element,k,seconds,1.,_seen=_seen) for k in ['red','green','blue','alpha']]
        return element.get(attribute,default)


class Session:
    def __init__(self, path):
        self.path=Path(path)
        self.data=datamodel.load(str(path),compact_arrays=True)
        self.root=self.data.root
        active=self.root.get('activeClip')
        if active is None or not kind(active,'DmeFilmClip'):
            raise ValueError('Select a full saved SFM session DMX, rather than an exported animation.')
        self.master=active
        settings=self.root.get('settings') or {}
        render=settings.get('renderSettings') or {}
        movie=settings.get('movieSettings') or {}
        fps=float(movie.get('OverridingFrameRate',render.get('frameRate',24))) if movie.get('IsOverridingFrameRate') else float(render.get('frameRate',24))
        self.fps=fps if 0<fps<=240 else 24.
        self.width=int(movie.get('width',1920))
        self.height=int(movie.get('height',1080))
        self.shots=[]
        self.sounds=[]
        seen=set()
        def walk(clip,clock,parent_clock,mapname):
            if eid(clip) in seen:return
            seen.add(eid(clip))
            mapname=clip.get('mapname') or mapname
            if kind(clip,'DmeFilmClip') and (clip.get('scene') is not None or clip.get('animationSets')):
                self.shots.append(Shot(clip,clock,parent_clock,mapname))
            for ch in clip_children(clip):
                if ch.get('mute',False):continue
                cc=clock.child(ch)
                if kind(ch,'DmeFilmClip'):walk(ch,cc,clock,mapname)
                elif kind(ch,'DmeSoundClip'):self.sounds.append((ch,cc))
        # The master is the timeline's container, not a placed shot.
        walk(active,Clock(),Clock(),active.get('mapname',''))
        if not self.shots:raise ValueError('No renderable shots found in the session.')
        self.shots.sort(key=lambda sh:sh.start)
        self.elements={eid(e):e for e in self.data.elements}

    def summary(self):
        result={'session':self.path.name,'fps':self.fps,'resolution':[self.width,self.height],'shots':[]}
        for sh in self.shots:
            models=[]
            for a in sh.element.get('animationSets',[]):
                gm=a.get('gameModel')
                if gm is not None:models.append({'name':a.name,'path':gm.get('modelName','')})
            result['shots'].append({'name':sh.element.name,'start':sh.start,'duration':sh.duration,'map':sh.map,
                                    'models':models,'channels':len(sh.curves),'issues':sorted(set(sh.issues))})
        result['sound_clips']=len(self.sounds)+sum(len(s.sounds) for s in self.shots)
        return result
