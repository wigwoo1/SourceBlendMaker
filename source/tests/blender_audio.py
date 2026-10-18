"""Blender integration test for packed, trimmed and animated sound clips."""
import array
import json
import math
from pathlib import Path
import sys
import wave
import time
import bpy

app=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(app))

if '--verify' not in sys.argv:
    import blender_worker as worker
    from session import Clock
    tone=Path('work/audio-tone.wav').resolve()
    with wave.open(str(tone),'wb') as stream:
        stream.setnchannels(1);stream.setsampwidth(2);stream.setframerate(48000)
        stream.writeframes(array.array('h',(int(12000*math.sin(2*math.pi*440*n/48000)) for n in range(6*48000))).tobytes())
    class Assets:
        def materialize(self,path):return tone
    class Shot:
        def value(self,element,key,t,default):return (.8 if t<4 else .4) if key=='volume' else default
    clip={'sound':{'soundname':'tone.wav','volume':.8},'timeFrame':{'start':2.,'duration':4.,'offset':1.,'scale':1.},'fadeIn':.5,'fadeOut':1.}
    class Clip(dict):name='Audio Envelope Test'
    output=Path('work/audio-envelopes.blend').resolve()
    worker.JOB={'output':str(output)}
    bpy.context.scene.render.fps=24
    worker.place_sounds(Assets(),[(Clip(clip),Clock(1.,1.))],bpy.context.scene,24,shot=Shot(),gain=.5)
    bpy.context.scene.frame_end=144
    bpy.ops.wm.save_as_mainfile(filepath=str(output))

scene=bpy.context.scene
strip=next(s for s in scene.sequence_editor.strips if s.type=='SOUND')
assert strip.sound.packed_file
assert strip.frame_final_start==49
assert strip.frame_offset_start==24
assert strip.frame_final_end==145
states=[]
for frame,expected in [(49,0.),(55,.2),(73,.4),(97,.2),(133,.1),(145,0.)]:
    scene.frame_set(frame)
    assert abs(strip.volume-expected)<1e-5,(frame,strip.volume,expected)
    states.append({'frame':frame,'volume':strip.volume})
if '--verify' in sys.argv:
    scene.frame_start=1;scene.frame_end=144
    mixed=Path('work/audio-envelope-mix.wav').resolve()
    bpy.ops.sound.mixdown(filepath=str(mixed),container='WAV',codec='PCM',format='S16',mixrate=48000)
    time.sleep(3)
    with wave.open(str(mixed),'rb') as stream:
        channels=stream.getnchannels();rate=stream.getframerate()
        samples=array.array('h',stream.readframes(stream.getnframes()))
    def rms(start,end):
        values=samples[round(start*rate)*channels:round(end*rate)*channels]
        return math.sqrt(sum(float(v)*v for v in values)/len(values))/32768
    silence=rms(.2,1.8);plateau=rms(2.7,3.7);quiet=rms(4.2,4.8)
    assert silence<1e-5,silence
    assert plateau>.05,plateau
    assert abs(quiet/plateau-.5)<.05,(quiet,plateau)
    Path('outputs/audio_validation.json').write_text(json.dumps({'packed':True,'trimmed':True,'reopened_native_volume_animation':True,'samples':states,'rendered_mix_rms':{'silence':silence,'plateau':plateau,'reduced_volume':quiet}},indent=2),encoding='utf-8')
print('AUDIO_VERIFIED',states)
