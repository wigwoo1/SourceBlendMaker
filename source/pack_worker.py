"""Background Blender supplies the bundled SourceIO archive readers."""
import sys
import json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from blender_worker import Assets,event
from project_pack import create_bundle,explicit_reference

if __name__=='__main__':
    job=json.loads(Path(sys.argv[sys.argv.index('--')+1]).read_text(encoding='utf-8'))
    assets=Assets(job)
    references=[]
    import datamodel
    try:
        data=datamodel.load(job['session'],compact_arrays=True)
        for element in data.elements:
            for key,value in element.items():
                values=value if isinstance(value,(list,tuple)) else [value]
                for item in values:
                    try:name=explicit_reference(key,item)
                    except ValueError as exc:
                        event('packing','Session reference ignored: '+str(exc));continue
                    if name:references.append(name)
    except Exception as exc:
        event('packing','Session reference audit unavailable: '+str(exc))
    providers=[]
    for child in assets.cm.children:
        providers.extend(getattr(child,'mount',[child]))
    result=create_bundle(job['session'],providers,job['bundle'],job.get('diagnostics',[]),lambda m:event('packing',m),references)
    print('SFM_PACK_RESULT '+json.dumps(result),flush=True)
