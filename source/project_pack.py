"""Conservative portable Source project bundles; never executes rig scripts."""
from pathlib import Path
import hashlib
import json
import os
import zipfile

def provider_files(provider,folder,excluded=()):
    if type(provider).__name__=='LooseFilesContentProvider':
        from SourceIO.library.utils import FileBuffer
        root=Path(str(provider.root))
        for path in (root/folder).rglob('*'):
            if path.is_file() and path.resolve() not in excluded:yield path.relative_to(root).as_posix(),FileBuffer(path)
    else:
        yield from provider.glob(folder+'/*')

ASSET_FOLDERS=('models','materials','maps','sound','scripts','particles','scenes','resource','cfg','elements')

def explicit_reference(key,value):
    if not isinstance(value,str):return None
    name=value.replace('\\','/').strip('/')
    if name.lower().endswith('.pcf'):
        from particle_paths import recorded_pcf_path
        name=recorded_pcf_path(value)
    if key=='mtlName':name='materials/'+name.removeprefix('materials/').removesuffix('.vmt')+'.vmt'
    elif key.lower()=='mapname':name='maps/'+name.removeprefix('maps/').removesuffix('.bsp')+'.bsp'
    if name.startswith(('models/','materials/','maps/','sound/','scripts/','particles/')) and Path(name).suffix.lower() in ('.mdl','.vmt','.vtf','.bsp','.wav','.mp3','.ogg','.py','.pcf','.dmx'):
        return name
    return None

def create_bundle(session, providers, output, diagnostics=(), progress=lambda message: None, references=()):
    """Pack mounted content in priority order, retaining first-path-wins resolution.

    This deliberately includes unused assets: Python rigs and material proxies can
    construct dependency names dynamically, so a minimal static scan is insufficient.
    Providers expose glob(pattern) -> (relative path, readable buffer).
    """
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    temporary=output.with_name(output.name+'.building')
    seen=set();entries=[];errors=[]
    manifest={'format':'SourceBlendMaker project bundle 1','strategy':'complete mounted asset folders',
              'includes_unused_assets':True,'files':entries,'read_errors':errors,
              'notes':['Built-in SFM engine binaries and Python runtime are not included.',
                       'Extract and select SourceProject as your asset folder; open its session.dmx.',
                       'Rig scripts are stored as files, never executed by the packer.']}
    try:
        with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED,compresslevel=1,allowZip64=True) as archive:
            archive.write(session,'SourceProject/session.dmx')
            for number,provider in enumerate(providers):
                for folder in ASSET_FOLDERS:
                    progress(f'Packing mount {number+1}: {folder} ({len(entries)} files)…')
                    for relative,buffer in provider_files(provider,folder,{output.resolve(),temporary.resolve()}):
                        name=str(relative).replace('\\','/').strip('/')
                        if ':' in name or '..' in name.split('/') or name.lower() in seen:
                            if hasattr(buffer,'close'):buffer.close()
                            continue
                        try:
                            buffer.seek(0);data=buffer.read()
                            archive.writestr('SourceProject/'+name,data)
                            seen.add(name.lower())
                            entries.append({'path':name,'size':len(data),'sha256':hashlib.sha256(data).hexdigest(),'mount_priority':number})
                        except Exception as exc:errors.append({'path':name,'error':str(exc)})
                        finally:
                            if hasattr(buffer,'close'):buffer.close()
            for index,path in enumerate(diagnostics):
                path=Path(path)
                if path.is_file():archive.write(path,f'diagnostics/{index+1}-{path.name}')
            archive.writestr('SourceProject/gameinfo.txt','"GameInfo" { "game" "SourceBlendMaker packed project" "FileSystem" { "SteamAppId" "1840" "SearchPaths" { "Game" "|gameinfo_path|." } } }')
            manifest['session_sha256']=hashlib.sha256(Path(session).read_bytes()).hexdigest()
            manifest['missing_explicit_session_paths']=sorted(path for path in set(references) if path.lower() not in seen)
            manifest['notes'].append('Missing-path list covers explicit session file references; it is not an exhaustive audit of dynamic script references.')
            archive.writestr('manifest.json',json.dumps(manifest,indent=2))
            archive.writestr('README.txt','Extract this ZIP. Select SourceProject as the SFM asset folder in SourceBlendMaker, and select SourceProject/session.dmx. This conservative bundle includes unused assets from mounted folders to preserve dynamically referenced rig/script dependencies. See manifest.json for read errors. Install SFM separately to edit the session in SFM.\n')
        os.replace(temporary,output)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return {'output':str(output),'files':len(entries),'errors':errors,'bytes':output.stat().st_size}
