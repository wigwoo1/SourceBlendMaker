"""VTF particle-sheet metadata and offline sprite UV selection.

Format references: Valve SDK public/vtf/vtf.h and the srctools VTF format reader
https://github.com/TeamSpen210/srctools/blob/master/src/srctools/vtf.py
Only the first coordinate set is rendered; multi-texture blends are reported.
If a requested sequence is missing but the VTF contains exactly one sequence,
the sole sequence is used and the bake report records the approximation.
"""
import math,struct

def validate_sequence_lifetime_order(names):
    # Installed slot29: sequence/lifetime-random use pass one; sequence-derived
    # lifetime uses pass two. The authored relative position does not change it.
    if 'Remap Initial Scalar' in names:
        raise ValueError('Unsupported sequence lifetime initializer order/remap')

def sequence_lifetime(sheet,sequence,parameters):
    # Installed SFM initializer metadata (member 0x70) defaults to 30 FPS.
    # Omission uses that default; explicitly invalid authored rates still fail.
    rate=float(parameters.get('Frames Per Second',30))
    if not math.isfinite(rate) or rate<=0:raise ValueError('Sequence lifetime requires positive Frames Per Second')
    entry=sheet.get(str(int(sequence)))
    if not entry or not entry.get('frames'):raise ValueError('Sequence lifetime requires texture-sheet frames for sequence '+str(sequence))
    return len(entry['frames'])/rate

def parse_vtf(data):
    if len(data)<16 or data[:4]!=b'VTF\0':raise ValueError('Invalid VTF header')
    major,minor,header=struct.unpack_from('<III',data,4)
    if major!=7:raise ValueError('Unsupported VTF major version')
    if minor<3:return {}
    if len(data)<80 or header>len(data):raise ValueError('Truncated VTF resource header')
    count=struct.unpack_from('<I',data,68)[0]
    if count>4096 or 80+count*8>header:raise ValueError('Invalid VTF resource dictionary')
    for index in range(count):
        tag,flags,offset=struct.unpack_from('<3sBI',data,80+index*8)
        if tag!=b'\x10\0\0':continue
        if flags&2:raise ValueError('Inline particle-sheet resource is invalid')
        if offset+4>len(data):raise ValueError('Truncated sheet resource size')
        size=struct.unpack_from('<I',data,offset)[0]
        if offset+4+size>len(data):raise ValueError('Truncated sheet resource')
        return parse_resource(data[offset+4:offset+4+size])
    return {}

def parse_resource(data):
    if len(data)<8:raise ValueError('Truncated sheet header')
    version,count=struct.unpack_from('<II',data)
    if version not in (0,1) or count>64:raise ValueError('Unsupported particle-sheet layout')
    result={};offset=8
    for _ in range(count):
        if offset+16>len(data):raise ValueError('Truncated sequence header')
        number,clamp,frames,duration=struct.unpack_from('<IIIf',data,offset);offset+=16
        if number>=64 or not 0<=frames<=100000:raise ValueError(f'Invalid sheet sequence {number}: {frames} frames')
        if not math.isfinite(duration) or duration<0 or (frames and duration<=0):raise ValueError('Invalid sequence duration')
        records=[];sets=1 if version==0 else 4
        for _ in range(frames):
            if offset+4+16*sets>len(data):raise ValueError('Truncated sheet frame')
            frame_duration=struct.unpack_from('<f',data,offset)[0];offset+=4
            coordinates=[list(struct.unpack_from('<4f',data,offset+16*i)) for i in range(sets)];offset+=16*sets
            if not math.isfinite(frame_duration) or frame_duration<0 or not all(math.isfinite(v) for c in coordinates for v in c):raise ValueError('Invalid sheet frame values')
            records.append({'duration':frame_duration,'coordinates':coordinates})
        # Some shipped sheets repeat IDs. Retain the final definition and flag it.
        duplicates=result.get(str(number),{}).get('duplicate_definitions',0)+int(str(number) in result)
        result[str(number)]={'clamp':bool(clamp),'duration':duration,'frames':records,'duplicate_definitions':duplicates}
    return result

def animation_rate(renderer):
    rate=float(renderer.get('animation rate',.1))
    if not math.isfinite(rate) or rate<0:raise ValueError('Invalid particle animation rate')
    return rate

def coordinates(sheet,sequence,age,lifetime,renderer,diagnostics=None):
    if not sheet:return ((0,0),(1,0),(1,1),(0,1))
    key=str(int(sequence))
    if key not in sheet:
        available=sorted(sheet,key=int)
        if len(available)==1:
            # Broken or mismatched PCFs commonly request a second sequence
            # from a single-sequence VTF. Preserve the visible sprite using
            # the only authored atlas, while recording that its appearance is
            # approximate. Do not guess when several candidate atlases exist.
            fallback=available[0]
            message=f'Particle requested missing texture sequence {key}; used sole available sequence {fallback}'
            if diagnostics is not None and message not in diagnostics:diagnostics.append(message)
            key=fallback
        else:
            requested=int(sequence);numbers=[int(value) for value in available]
            if requested<numbers[0] or requested>numbers[-1]:
                # Some shipped PCFs allow an inclusive Sequence Random upper
                # bound that is one past the highest VTF sequence. Clamp only
                # out-of-range requests; internal gaps remain ambiguous.
                fallback=str(numbers[0] if requested<numbers[0] else numbers[-1])
                message=f'Particle requested out-of-range texture sequence {key}; clamped to boundary sequence {fallback}'
                if diagnostics is not None and message not in diagnostics:diagnostics.append(message)
                key=fallback
            else:
                raise ValueError('Particle texture has no sequence '+key+'; available sequences: '+', '.join(available))
    entry=sheet[key];frames=entry['frames'];total=entry['duration']
    if not frames or total<=0:raise ValueError('Particle texture sequence '+key+' has no frames')
    rate=animation_rate(renderer)
    if renderer.get('animation_fit_lifetime',False):time=age/max(lifetime,1e-9)*total
    elif renderer.get('use animation rate as FPS',False):time=age*rate*total/len(frames)
    else:time=age*rate*total
    time=min(time,math.nextafter(total,0)) if entry['clamp'] else time%total
    selected=frames[-1]
    for frame in frames:
        if time<frame['duration']:selected=frame;break
        time-=frame['duration']
    left,top,right,bottom=selected['coordinates'][0]
    return ((left,1-bottom),(right,1-bottom),(right,1-top),(left,1-top))
