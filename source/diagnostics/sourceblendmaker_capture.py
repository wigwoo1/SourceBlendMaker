"""Read-only current-shot diagnostic; compatible with SFM's Python 2.7.

Run inside SFM after selecting the benchmark frame. No rig, pose, time,
material or session attribute is changed. Runtime SFM validation is pending.
"""
import json

def serialize(value):
    if value is None or isinstance(value, (bool, int, float)):
        return value
    try:
        strings = (basestring,)
    except NameError:
        strings = (str,)
    if isinstance(value, strings):
        return value
    try:
        return [serialize(item) for item in value]
    except TypeError:
        return {'text': str(value), 'python_type': type(value).__name__}

def capture(sfm_api, frame_label, clip_editor=None):
    shot = sfm_api.GetCurrentShot()
    shot_source = 'sfm.GetCurrentShot'
    if shot is None and clip_editor is not None:
        selected = list(clip_editor.GetSelectedShots())
        if len(selected) == 1:
            shot = selected[0]
            shot_source = 'sfmClipEditor.GetSelectedShots'
        elif len(selected) > 1:
            raise ValueError('Select exactly one shot in the Clip Editor before capturing.')
    if shot is None:
        raise ValueError('Select a shot before capturing.')
    result = {'schema': 1, 'frame_label': str(frame_label),
              'shot_lookup': shot_source,
              'shot': str(shot.GetName()), 'models': [], 'particles': [], 'errors': [],
              'semantics': 'Current SFM element values; not a vertex-position export.'}
    def read(element, name, default=None):
        try:
            return getattr(element, name)
        except Exception:
            return default
    def transform_record(element):
        return {'name': str(element.GetName()),
                'position': serialize(read(element, 'position')),
                'orientation': serialize(read(element, 'orientation')),
                'scale': serialize(read(element, 'scale'))}
    scene = read(shot, 'scene')
    pending = [(scene, [])] if scene is not None else []
    visited = set()
    while pending:
        dag, ancestors = pending.pop()
        if id(dag) in visited:
            continue
        visited.add(id(dag))
        if len(visited) > 10000:
            result['errors'].append('Particle scene traversal exceeded 10000 elements.')
            break
        transform = read(dag, 'transform')
        lineage = ancestors + ([transform_record(transform)] if transform is not None else [])
        particle_type = read(dag, 'particleSystemType')
        if particle_type is not None:
            result['particles'].append({
                'name': str(dag.GetName()), 'particleSystemType': serialize(particle_type),
                'visible': serialize(read(dag, 'visible')),
                'simulating': serialize(read(dag, 'simulating')),
                'emitting': serialize(read(dag, 'emitting')),
                'simulationTimeScale': serialize(read(dag, 'simulationTimeScale')),
                'randomSeed': serialize(read(dag, 'randomSeed')),
                'ancestor_transforms': lineage,
                'control_points': [transform_record(cp) for cp in read(dag, 'controlPoints', [])],
                'semantics': 'Current element-local controls and ancestor transforms; not engine particle vertices or lighting queries.'})
        for child in read(dag, 'children', []):
            if child is not None:
                pending.append((child, lineage))
    camera = read(shot, 'camera')
    if camera is not None:
        transform = read(camera, 'transform')
        result['shot_camera'] = {'name': str(camera.GetName()),
                                 'fieldOfView': serialize(read(camera, 'fieldOfView')),
                                 'position': serialize(read(transform, 'position')),
                                 'orientation': serialize(read(transform, 'orientation')),
                                 'semantics': 'Shot camera; the viewport may display a different Work Camera.'}
    for animation in read(shot, 'animationSets', []):
        model = read(animation, 'gameModel')
        if model is None:
            continue
        record = {'name': str(animation.GetName()), 'model_path': str(read(model, 'modelName', '')),
                  'flex_names': serialize(read(model, 'flexnames', [])),
                  'flex_weights': serialize(read(model, 'flexWeights', [])),
                  'controllers': [], 'materials': [], 'bones': []}
        for control in read(model, 'globalFlexControllers', []):
            record['controllers'].append({'name': str(control.GetName()),
                                          'value': serialize(read(control, 'flexWeight'))})
        for bone in read(model, 'bones', []):
            record['bones'].append({'name': str(bone.GetName()),
                                    'position': serialize(read(bone, 'position')),
                                    'orientation': serialize(read(bone, 'orientation'))})
        for material in read(model, 'materials', []):
            item = {'name': str(material.GetName()), 'path': str(read(material, 'mtlName', '')), 'attributes': []}
            try:
                for attribute in material.iterAttrs():
                    name = attribute.GetName()
                    if name.startswith('$'):
                        item['attributes'].append({'name': str(name), 'type': int(attribute.GetType()),
                                                   'value': serialize(read(material, name)), 'text': str(attribute)})
            except Exception as exc:
                result['errors'].append('Material attribute capture: '+str(exc))
            record['materials'].append(item)
        result['models'].append(record)
    if not result['models'] and not result['particles']:
        result['errors'].append('No game models or particle systems captured; verify the active shot.')
    return result

def main():
    import sfm
    import sfmClipEditor
    from PySide import QtGui
    label, accepted = QtGui.QInputDialog.getText(None, 'SourceBlendMaker diagnostic',
                                                'Current SFM frame label (for example 2578):')
    if not accepted:
        return
    filename, unused = QtGui.QFileDialog.getSaveFileName(None, 'Save current-shot diagnostic',
                                                        'sourceblendmaker-sfm-pose.json', '*.json')
    if not filename:
        return
    if not filename.lower().endswith('.json'):
        filename += '.json'
    try:
        result = capture(sfm, label, sfmClipEditor)
        with open(filename, 'w') as output:
            json.dump(result, output, indent=2)
        QtGui.QMessageBox.information(None, 'SourceBlendMaker diagnostic',
                                      'Captured {0} models and {1} particle systems. Session unchanged.\n{2}'.format(len(result['models']), len(result['particles']), filename))
    except Exception as exc:
        QtGui.QMessageBox.critical(None, 'Capture failed', str(exc))

if __name__ == '__main__':
    main()
