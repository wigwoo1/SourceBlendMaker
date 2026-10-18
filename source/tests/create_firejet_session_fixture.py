"""Clone an SFM session and replace one particle system with Portal 2 fire_jet_01.

Usage: python create_firejet_session_fixture.py input.dmx output.dmx [system-name]
The source DMX is read-only; the selected system keeps its original control-point DAG.
"""
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import datamodel
from particles import is_system


def create(source,target,system_name='I dunno1'):
    source=Path(source);target=Path(target)
    data=datamodel.load(str(source),compact_arrays=True)
    systems=[element for element in data.elements if is_system(element)]
    selected=next((element for element in systems if element.name==system_name),None)
    if selected is None:raise ValueError(f'Particle system not found: {system_name}')
    for system in systems:
        is_selected=system==selected
        system['visible']=is_selected
        system['emitting']=is_selected
        system['simulating']=is_selected
        if is_selected:system['particleSystemType']='fire_jet_01'
    for element in data.elements:
        if element.type.lstrip('C')=='DmeAnimationSet' and element.get('particle system')==selected:
            element['particleFiles']=datamodel.make_array(['particles\\fire_01.pcf'],str)
        children=element.get('children')
        if isinstance(children,datamodel._ElementArray):
            kept=[child for child in children if not is_system(child) or child==selected]
            if len(kept)!=len(children):element['children']=datamodel.make_array(kept,datamodel.Element)
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes(data.echo('keyvalues2',4).encode('utf-8'))
    return {'source':str(source),'fixture':str(target),'selected_system':selected.name,
            'particle_effect':selected.get('particleSystemType'),'systems_in_source':len(systems),
            'systems_in_fixture':1,'pcf_hint':'particles/fire_01.pcf',
            'dmx_format_version':data.format_ver,'fixture_encoding':'keyvalues2 4'}


if __name__=='__main__':
    if len(sys.argv) not in (3,4):raise SystemExit(__doc__)
    print(create(sys.argv[1],sys.argv[2],sys.argv[3] if len(sys.argv)==4 else 'I dunno1'))
