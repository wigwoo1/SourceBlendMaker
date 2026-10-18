"""Resolve named Source sounds through mounted manifests, without randomness."""
from pathlib import PurePosixPath

FLAGS='*#@><^)}$!?'

def relative_sound(value):
    value=str(value).lstrip(FLAGS).replace('\\','/').strip('/')
    if ':' in value or '..' in value.split('/'):
        raise ValueError('Sound path must be relative to the selected Source assets')
    return value if value.lower().startswith('sound/') else 'sound/'+value


class SoundScripts:
    def __init__(self,assets,maps=()):
        self.assets=assets;self.entries={};self.issues=[]
        from SourceIO.library.utils import kv1
        def parse(buffer,name):
            buffer.seek(0)
            return kv1.load_bytes(buffer.read(),name=str(name))
        filenames=[]
        for name,buffer in assets.cm.glob('scripts/game_sounds_manifest.txt'):
            try:
                manifest=parse(buffer,name).get('game_sounds_manifest')
                if manifest:
                    filenames.extend(str(v) for k,v in manifest.items() if k in ('precache_file','preload_file'))
            except Exception as exc:self.issues.append(f'Sound manifest {name}: {exc}')
        for name in dict.fromkeys(filenames):
            try:
                buffer=assets.buffer(name)
                if buffer is None:continue
                for key,entry in parse(buffer,name).items():
                    if hasattr(entry,'get'):self.entries.setdefault(key.lower(),entry)
            except Exception as exc:self.issues.append(f'Sound script {name}: {exc}')
        # Map-specific definitions override the general sound library.
        for mapname in maps:
            name='maps/'+PurePosixPath(str(mapname).replace('\\','/')).stem+'_level_sounds.txt'
            buffer=assets.buffer(name)
            if buffer:
                try:
                    for key,entry in parse(buffer,name).items():
                        if hasattr(entry,'get'):self.entries[key.lower()]=entry
                except Exception as exc:self.issues.append(f'Map sound script {name}: {exc}')

    def resolve(self,sound):
        direct=str(sound.get('soundname',''))
        if direct and PurePosixPath(direct).suffix.lower() in ('.wav','.mp3','.ogg','.flac'):
            return relative_sound(direct),None
        name=str(sound.get('gameSoundName') or direct)
        entry=self.entries.get(name.lower())
        if entry is None:raise FileNotFoundError(f'Named sound script not found: {name}')
        wave=entry.get('wave');random=entry.get('rndwave')
        choices=[wave] if wave else (random.get_all('wave') if random else [])
        if not choices:raise ValueError(f'Named sound has no wave: {name}')
        # DMX does not retain the engine random seed. Prefer the first available
        # candidate and disclose that choice rather than silently randomizing.
        for candidate in choices:
            rel=relative_sound(candidate)
            if self.assets.buffer(rel) is not None:
                return rel,{'name':name,'candidates':len(choices),'selected':rel,'random_choice_approximation':len(choices)>1}
        raise FileNotFoundError(f'No audio candidate found for {name}: {choices}')
