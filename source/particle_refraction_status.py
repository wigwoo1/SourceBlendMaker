"""Keep simulation geometry and compositor render success distinct in reports."""
def failed(descriptor,material_paths,reason):
    paths={str(p).replace('\\','/').removeprefix('materials/').lower() for p in material_paths}
    changed=0
    for record in descriptor.get('bake',[]):
        path=str(record.get('material_path','')).replace('\\','/').removeprefix('materials/').lower()
        if path in paths and record.get('rendered'):
            record.update(rendered=False,refraction_compositor_installed=False,failure_category='refraction_compositor_failed',reason=str(reason));changed+=1
    descriptor['rendered']=bool(descriptor.get('bake')) and all(r.get('rendered',False) for r in descriptor['bake'])
    return changed
