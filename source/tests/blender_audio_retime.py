"""Measure retiming, pitch, offsets and reverse audio in a reopened mix."""
from pathlib import Path
import sys,json,wave,time
import numpy as np
import bpy
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
if '--verify' not in sys.argv:
    import blender_worker as w
    from session import Clock
    tone=Path('work/retime-tone.wav').resolve();rate=48000
    t=np.arange(rate*6)/rate;freq=np.where(t<2,440,np.where(t<4,660,880))
    with wave.open(str(tone),'wb') as stream:
        stream.setnchannels(1);stream.setsampwidth(2);stream.setframerate(rate)
        stream.writeframes((12000*np.sin(2*np.pi*freq*t)).astype('<i2').tobytes())
    class Assets:
        def materialize(self,name):return tone
    class Clip(dict):name='Audio retime test'
    class Shot:
        def value(self,e,key,t,default):return 100+50*(t-9) if key=='pitch' and e.get('animated') else default
    clips=[]
    for offset,scale,clock,pitch,animated in [(1.5,2,Clock(-.75,.5),100,False),(2,1,Clock(1,1),150,False),(5,-2,Clock(8.5,-.5),100,False),(0,1,Clock(9,1),100,True)]:
        clips.append((Clip(sound={'soundname':'tone.wav','pitch':pitch,'animated':animated},timeFrame={'offset':offset,'scale':scale,'duration':2}),clock))
    output=Path('work/audio-retime.blend').resolve();w.JOB={'output':str(output)}
    scene=bpy.context.scene;scene.render.fps=24;scene.frame_end=288
    w.place_sounds(Assets(),clips,scene,24,shot=Shot())
    assert not w.REPORT['errors'],w.REPORT
    assert all(a.get('audio_baked') for a in w.REPORT['assets'] if a['type']=='sound')
    bpy.ops.wm.save_as_mainfile(filepath=str(output))
else:
    scene=bpy.context.scene
    strips=[s for s in scene.sequence_editor.strips if s.type=='SOUND']
    assert len(strips)==4 and all(s.sound.packed_file for s in strips)
    assert [s.frame_final_duration for s in strips]==[48]*4
    output=Path('work/audio-retime-mix.wav').resolve()
    bpy.ops.sound.mixdown(filepath=str(output),container='WAV',codec='PCM',format='S16',mixrate=48000);time.sleep(3)
    with wave.open(str(output),'rb') as stream:
        rate=stream.getframerate();channels=stream.getnchannels();samples=np.frombuffer(stream.readframes(stream.getnframes()),dtype='<i2').reshape(-1,channels).mean(axis=1)
    results=[]
    for start,end,expected in [(.1,.3,880),(.7,.9,1320),(3.2,3.4,990),(6.1,6.3,1760),(6.7,6.9,1320),(9.1,9.2,473),(9.7,9.8,605)]:
        part=samples[round(start*rate):round(end*rate)]
        spectrum=np.abs(np.fft.rfft(part*np.hanning(len(part))));frequency=np.argmax(spectrum)*rate/len(part)
        assert abs(frequency-expected)<20,(start,frequency,expected)
        results.append({'interval':[start,end],'expected_hz':expected,'measured_hz':frequency})
    Path('outputs/audio_retime_validation.json').write_text(json.dumps({'packed_reopened':True,'duration_preserved':True,'speed_and_pitch':True,'reverse_audio':True,'animated_pitch':True,'measurements':results},indent=2))
    print('AUDIO RETIMING TEST PASSED',results)
