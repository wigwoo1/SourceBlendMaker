"""Mounted manifest resolution followed by native packed sound save/reopen."""
from pathlib import Path
import sys,json,wave,array,math
import bpy
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

if '--verify' not in sys.argv:
    import blender_worker as worker
    from sound_scripts import SoundScripts
    from session import Clock
    from SourceIO.library.utils import MemoryBuffer
    texts={
      'scripts/game_sounds_manifest.txt':'game_sounds_manifest { precache_file "scripts/test.txt" preload_file "scripts/second.txt" }',
      'scripts/test.txt':'"Named.Tone" { wave "*test/tone.wav" } "Random.Tone" { rndwave { wave "missing.wav" wave "#test/tone.wav" } }',
      'scripts/second.txt':'"Other.Tone" { wave "test/tone.wav" }',
      'maps/test_level_sounds.txt':'"Named.Tone" { wave "test/map-tone.wav" }'}
    root=Path('work/soundscripts.assets').resolve();(root/'sound/test').mkdir(parents=True,exist_ok=True)
    for name in ('tone.wav','map-tone.wav'):
        with wave.open(str(root/'sound/test'/name),'wb') as stream:
            stream.setnchannels(1);stream.setsampwidth(2);stream.setframerate(48000)
            stream.writeframes(array.array('h',(int(10000*math.sin(2*math.pi*440*n/48000)) for n in range(48000))).tobytes())
    class Assets:
        sound_scripts={}
        def __init__(self):self.cm=self
        def glob(self,pattern):yield 'manifest',MemoryBuffer(texts[pattern].encode())
        def buffer(self,name):
            if name in texts:return MemoryBuffer(texts[name].encode())
            path=root/name
            return MemoryBuffer(path.read_bytes()) if path.is_file() else None
        def materialize(self,name):return root/name
    assets=Assets();scripts=SoundScripts(assets,['maps/test.bsp']);assert not scripts.issues,scripts.issues
    assert scripts.resolve({'gameSoundName':'Named.Tone'})[0]=='sound/test/map-tone.wav'
    assert scripts.resolve({'gameSoundName':'Other.Tone'})[0]=='sound/test/tone.wav'
    assert scripts.resolve({'soundname':'*test/tone.wav'})[1] is None
    assert scripts.resolve({'gameSoundName':'Random.Tone'})[1]['candidates']==2
    class Clip(dict):name='Named game sound'
    class Shot:
        map='maps/test.bsp'
        def value(self,e,key,t,default):return default
    output=Path('work/soundscripts.blend').resolve();worker.JOB={'output':str(output)}
    clip=Clip(sound={'gameSoundName':'Named.Tone'},timeFrame={'duration':1})
    worker.place_sounds(assets,[(clip,Clock())],bpy.context.scene,24,shot=Shot())
    assert not worker.REPORT['errors'],worker.REPORT
    bpy.ops.wm.save_as_mainfile(filepath=str(output))
else:
    strip=next(s for s in bpy.context.scene.sequence_editor.strips if s.type=='SOUND')
    assert strip.sound.packed_file and strip.sound.filepath.endswith('map-tone.wav')
    Path('outputs/sound_scripts_validation.json').write_text(json.dumps({'mounted_manifest':True,'map_override':True,'random_variant_reported':True,'packed_audio_reopened':True,'path':strip.sound.filepath},indent=2))
    print('NAMED SOUND TEST PASSED')
