"""Clone an SFM DMX session with one selected particle system/effect.

Usage: python create_particle_session_fixture.py input.dmx output.dmx
       [system-name] [effect-name] [pcf-hint]
The source DMX is read-only. Other particle systems are hidden and detached
from the session hierarchy so a native conversion can focus on one definition.
"""
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import datamodel
from particles import is_system


def create(source,target,system_name,effect_name,pcf_hint):
    source=Path(source);target=Path(target)
    data=datamodel.load(str(source),compact_arrays=False)
    systems=[element for element in data.elements if is_system(element)]
    selected=next((element for element in systems if element.name==system_name),None)
    if selected is None:raise ValueError(f'Particle system not found: {system_name}')
    for system in systems:
        is_selected=system==selected
        system['visible']=is_selected
        system['emitting']=is_selected
        system['simulating']=is_selected
        if is_selected:system['particleSystemType']=effect_name
    # The worker scans every reachable DmeGameParticleSystem in the DMX, not
    # just the systems visible in the scene. Clear references to other systems
    # so a one-effect test does not accidentally bake the source session's
    # entire particle library. The DMX writer serializes the graph reachable
    # from its root, so unreferenced systems are omitted from the fixture.
    discarded={system for system in systems if system!=selected}
    for element in data.elements:
        for key,value in list(element.items()):
            if isinstance(value,datamodel.Element) and value in discarded:
                element[key]=None
            elif isinstance(value,datamodel._ElementArray):
                kept=[item for item in value if item not in discarded]
                if len(kept)!=len(value):element[key]=datamodel.make_array(kept,datamodel.Element)
        if element.type.lstrip('C')=='DmeAnimationSet' and element.get('particle system')==selected:
            element['particleFiles']=datamodel.make_array([pcf_hint.replace('/','\\')],str)
        children=element.get('children')
        if isinstance(children,datamodel._ElementArray):
            kept=[child for child in children if not is_system(child) or child==selected]
            if len(kept)!=len(children):element['children']=datamodel.make_array(kept,datamodel.Element)
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes(data.echo('keyvalues2',4).encode('utf-8'))
    return {'source':str(source),'fixture':str(target),'selected_system':selected.name,
            'particle_effect':effect_name,'pcf_hint':pcf_hint,
            'systems_in_source':len(systems),'systems_in_fixture':1,
            'dmx_format_version':data.format_ver,'fixture_encoding':'keyvalues2 4'}


if __name__=='__main__':
    if len(sys.argv)!=6:raise SystemExit(__doc__)
    print(create(*sys.argv[1:]))

