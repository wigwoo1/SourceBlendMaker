"""Scan selected sessions using the same mounts and PCF resolver as conversion."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_worker import Assets, event
from session import Session, eid
from particles import Definitions, is_system
from particle_option_scan import detect


def scan(job):
    assets = Assets(job)
    definitions = Definitions(assets)
    material_cache = {}
    result = {'sessions': []}
    from SourceIO.library.source1.vmt import VMT
    for path in job['scan_sessions']:
        entry = {'session': path, 'effects': [], 'errors': []}
        result['sessions'].append(entry)
        event('scan', 'Scanning particle options: ' + path)
        try:
            session = Session(path)
            hints = {eid(e.get('particle system')): e.get('particleFiles', []) for e in session.data.elements
                     if e.type.lstrip('C') == 'DmeAnimationSet' and e.get('particle system') is not None}
            for system in session.data.elements:
                if not is_system(system): continue
                try:
                    descriptor = definitions.describe(system, hints.get(eid(system), []))
                    for definition in descriptor['definitions']:
                        material = None
                        name = definition['parameters'].get('material')
                        if name:
                            rel = 'materials/' + name
                            if rel not in material_cache:
                                try:
                                    buf = assets.buffer(rel)
                                    if buf is None: raise FileNotFoundError(rel)
                                    vmt = VMT(buf, assets.TinyPath(rel), assets.cm)
                                    material_cache[rel] = ({'shader': vmt.shader, 'spline_type': vmt.get_int('$splinetype', 0)}, None)
                                except Exception as exc: material_cache[rel] = (None, str(exc))
                            material, error = material_cache[rel]
                            if error: entry['errors'].append(system.name + ' / ' + definition['name'] + ': ' + error)
                        entry['effects'].append({'system': system.name, 'definition': definition['name'],
                                                 'options': detect(definition, material)})
                except Exception as exc: entry['errors'].append(system.name + ': ' + str(exc))
        except Exception as exc: entry['errors'].append(str(exc))
    result['lookup'] = definitions.lookup_summary()
    return result


if __name__ == '__main__':
    job = json.loads(Path(sys.argv[sys.argv.index('--') + 1]).read_text(encoding='utf-8'))
    print('SFM_SCAN_RESULT ' + json.dumps(scan(job)), flush=True)
