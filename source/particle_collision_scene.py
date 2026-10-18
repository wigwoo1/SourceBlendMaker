"""Eligibility checks for world-brush-only particle collision development."""
import struct
import re
from bsp_collision import read_world_brushes
from particle_brush_trace import PreparedBrushTracer

# Installed pet.dll helper 0x101f6a30 passes this mask at 0x101f6a98.
# This verifies the query mask, not Source cached-plane response parity.
TRACE_CONTENTS_MASK=0x0200400B


def required(descriptors):
    for descriptor in descriptors:
        for definition in descriptor.get('definitions',[]):
            for module in definition.get('modules',{}).get('constraints',[]):
                if module.get('function')=='Collision via traces' and module.get('parameters',{}).get('operator enabled',True):
                    return True
    return False


def prepare(session,shot,assets):
    """Resolve through configured mounts, without any hard-coded game path."""
    if not shot.map:raise ValueError('Particle trace collision requires a session map')
    path=str(shot.map).replace('\\','/')
    if not path.startswith('maps/'):path='maps/'+path
    if not path.lower().endswith('.bsp'):path+='.bsp'
    if any(part in ('','..') for part in path.split('/')) or ':' in path:
        raise ValueError('Invalid particle collision map path')
    count=sum(e.type.lstrip('C')=='DmeGameModel' for e in session.elements.values())
    if count:raise ValueError('Particle collision with session models is not implemented')
    buffer=assets.buffer(path)
    if buffer is None:raise ValueError('Missing particle collision map: '+path)
    buffer.seek(0)
    provider,report=world_provider(buffer.read(),count)
    report['map']=path
    return provider,report


def _check_entities(payload):
    """Reject geometry-bearing entities, including dynamic props outside sprp."""
    text=payload.rstrip(b'\0').decode('utf-8',errors='strict')
    token=re.compile(r'\s+|//[^\n]*|[{}]|"(?:[^"\\]|\\.)*"')
    tokens=[];cursor=0
    for match in token.finditer(text):
        if match.start()!=cursor:raise ValueError('Unsupported collision entity syntax')
        value=match.group();cursor=match.end()
        if not value.isspace() and not value.startswith('//'):tokens.append(value)
    if cursor!=len(text):raise ValueError('Unsupported collision entity syntax')
    index=0
    while index<len(tokens):
        if tokens[index]!='{':raise ValueError('Invalid collision entity block')
        index+=1;fields={}
        while index<len(tokens) and tokens[index]!='}':
            if index+1>=len(tokens) or not all(t.startswith('"') for t in tokens[index:index+2]):
                raise ValueError('Invalid collision entity fields')
            key,value=tokens[index:index+2];index+=2
            fields[key[1:-1].lower()]=value[1:-1]
        if index>=len(tokens):raise ValueError('Unclosed collision entity block')
        index+=1
        if fields.get('model') or fields.get('classname','').lower().startswith(('prop_','func_')):
            raise ValueError('Particle collision with map model or brush entities is not implemented')


def world_provider(raw,session_model_count):
    if session_model_count!=0:raise ValueError('Particle collision with session models is not implemented')
    geometry=read_world_brushes(raw)
    def lump(index):
        offset,length,version,compressed=struct.unpack_from('<4i',raw,8+16*index)
        if offset<0 or length<0 or offset+length>len(raw):raise ValueError('Collision scene lump outside BSP')
        if compressed or raw[offset:offset+4]==b'LZMA':raise ValueError('Compressed collision scene inspection unsupported')
        return raw[offset:offset+length]
    if len(lump(14))!=48:raise ValueError('Particle collision with brush submodels is not implemented')
    _check_entities(lump(0))
    if lump(26):raise ValueError('Particle collision with displacement surfaces is not implemented')
    game=lump(35)
    if game:
        if len(game)<4:raise ValueError('Truncated collision game lump')
        count=struct.unpack_from('<i',game)[0]
        if count<0 or 4+16*count>len(game):raise ValueError('Invalid collision game lump directory')
        for i in range(count):
            name,flags,version,offset,length=struct.unpack_from('<4sHHii',game,4+16*i)
            if name not in (b'prps',b'sprp'):continue
            if offset<0 or length<4 or offset+length>len(raw):raise ValueError('Invalid collision static prop lump')
            payload=raw[offset:offset+length]
            if flags&1 or payload[:4]==b'LZMA':raise ValueError('Compressed collision static props unsupported')
            models=struct.unpack_from('<i',payload)[0]
            cursor=4+128*models
            if models<0 or cursor+4>len(payload):raise ValueError('Invalid collision static prop model table')
            leaves=struct.unpack_from('<i',payload,cursor)[0];cursor+=4+2*leaves
            if leaves<0 or cursor+4>len(payload):raise ValueError('Invalid collision static prop leaf table')
            props=struct.unpack_from('<i',payload,cursor)[0]
            if props!=0:raise ValueError('Particle collision with static props is not implemented')
    return PreparedBrushTracer(geometry['brushes'],contents_mask=TRACE_CONTENTS_MASK),{'world_brush_count':len(geometry['brushes']),
        'scope':'World brush geometry; no model, displacement or brush entity collision required',
        'source_engine_parity':False,'production_enabled':False,
        'contents_mask':TRACE_CONTENTS_MASK,'contents_filter_verified':True,
        'limitations':['World brushes only; collision with models and displacements is not implemented',
                       'Source cached-plane tracing and boundary epsilon are not reproduced']}
