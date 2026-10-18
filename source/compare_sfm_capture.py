"""Compare a current-shot SFM capture with saved DMX controller sampling."""
import argparse,json,math
from pathlib import Path

def compare(session,capture,source_shot_frame,tolerance=1e-5):
    if not math.isfinite(source_shot_frame) or source_shot_frame<0:
        raise ValueError('Source shot frame must be finite and nonnegative')
    if not math.isfinite(tolerance) or tolerance<0:
        raise ValueError('Comparison tolerance must be finite and nonnegative')
    shots=[shot for shot in session.shots if shot.element.name==capture.get('shot')]
    if len(shots)!=1:raise ValueError('Capture shot does not uniquely match the saved session')
    shot=shots[0];time=shot.start+float(source_shot_frame)/session.fps
    models={animation.name:animation.get('gameModel') for animation in shot.element.get('animationSets',[])}
    result={'shot':shot.element.name,'source_shot_frame_zero_based':source_shot_frame,
            'corresponding_blender_shot_frame':source_shot_frame+1,'source_seconds':time,
            'capture_errors':capture.get('errors',[]),'checks':[],'mismatches':[],
            'missing':[],'source_mesh_equivalence_verified':False}
    captured_camera=capture.get('shot_camera')
    if captured_camera:
        camera=shot.element.get('camera')
        result['camera_comparison']={'source_viewport_camera_verified':False}
        if camera is None or camera.name!=captured_camera.get('name'):
            result['camera_comparison']['error']='Shot camera identity does not match'
        else:
            try:
                actual=float(captured_camera['fieldOfView'])
                expected=float(shot.value(camera,'fieldOfView',time,45.))
                if not math.isfinite(actual) or not math.isfinite(expected):raise ValueError()
                result['camera_comparison'].update(sfm_horizontal_fov=actual,dmx_horizontal_fov=expected,
                                                   horizontal_fov_matches=abs(actual-expected)<=tolerance)
            except (ValueError,TypeError,KeyError):
                result['camera_comparison']['error']='Camera FOV not numeric'
    for model in capture.get('models',[]):
        gm=models.get(model['name'])
        if gm is None:
            result['missing'].append({'model':model['name'],'reason':'No matching animation set'});continue
        normalize=lambda path:str(path).replace('\\','/').lower()
        if normalize(gm.get('modelName',''))!=normalize(model.get('model_path','')):
            result['missing'].append({'model':model['name'],'reason':'Model asset path differs'});continue
        controllers={controller.name:controller for controller in gm.get('globalFlexControllers',[])}
        for controller in model.get('controllers',[]):
            name=controller['name'];element=controllers.get(name)
            if element is None:
                result['missing'].append({'model':model['name'],'controller':name,'reason':'No matching controller'});continue
            try:
                actual=float(controller['value']);sample=float(shot.value(element,'flexWeight',time,element.get('flexWeight',0)))
                if not math.isfinite(actual) or not math.isfinite(sample):raise ValueError('Nonfinite controller value')
            except (ValueError,TypeError):
                result['missing'].append({'model':model['name'],'controller':name,'reason':'Controller value not numeric'});continue
            check={'model':model['name'],'controller':name,'sfm_value':actual,'dmx_sample':sample,'difference':abs(actual-sample)}
            result['checks'].append(check)
            if check['difference']>tolerance:result['mismatches'].append(check)
    result['all_captured_controllers_match']=bool(result['checks']) and not any(result[key] for key in ('capture_errors','missing','mismatches'))
    if capture.get('particles'):
        from compare_particle_capture import compare_particles
        result['particle_comparison']=compare_particles(shot,capture['particles'],time,tolerance)
        if result['capture_errors']:result['particle_comparison']['all_compared_particle_inputs_match']=False
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session',required=True);parser.add_argument('--capture',required=True)
    parser.add_argument('--source-shot-frame',required=True,type=float,help='Zero-based frame within the captured SFM shot')
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    if args.source_shot_frame<0:parser.error('Source shot frame must be nonnegative')
    from session import Session
    result=compare(Session(args.session),json.loads(Path(args.capture).read_text()),args.source_shot_frame)
    Path(args.output).write_text(json.dumps(result,indent=2),encoding='utf-8')
    print('Compared {0} controls; {1} mismatches; {2} missing'.format(len(result['checks']),len(result['mismatches']),len(result['missing'])))
    particles=result.get('particle_comparison')
    if particles:
        print('Compared {0} particle inputs; {1} mismatches; {2} missing'.format(
            len(particles['checks']),len(particles['mismatches']),len(particles['missing'])))
    if result['capture_errors']:
        print('Capture reported {0} errors; inspect the JSON before interpreting matches.'.format(len(result['capture_errors'])))

if __name__=='__main__':main()
