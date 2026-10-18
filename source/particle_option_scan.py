"""Read-only option detection. Authored feature presence is not conversion proof."""
LABELS = {
    'experimental_noise': 'Particle noise initializers',
    'experimental_pull_lock': 'Forces with translation locks',
    'experimental_parent': 'Parent-particle spawning',
    'experimental_tint': 'Map-light tint',
    'experimental_refraction': 'Particle refraction',
    'experimental_delayed_decay': 'Delayed particle decay',
    'experimental_pull': 'Particle pull forces',
    'experimental_spline': 'Spline ropes and rings',
    'experimental_partial_lock': 'Particle attachment fades',
}


def detect(definition, material=None):
    """Return option -> reasons, including enabled child definitions via caller."""
    found = {}
    def add(key, reason):
        found.setdefault(key, []).append(reason)
    groups = {g: [m for m in modules if m.get('parameters', {}).get('operator enabled', True)]
              for g, modules in definition.get('modules', {}).items()}
    initial = groups.get('initializers', [])
    operators = groups.get('operators', [])
    forces = groups.get('forces', [])
    pull = any(m['function'].casefold() == 'pull towards control point' for m in forces)
    twist = any(m['function'] == 'twist around axis' for m in forces)
    if pull: add('experimental_pull', 'Pull towards control point')
    locks = [m for m in operators if m['function'] == 'Movement Lock to Control Point']
    if locks and (pull or twist): add('experimental_pull_lock', 'Pull/twist force combined with a control-point lock')
    for m in initial:
        name, p = m['function'], m['parameters']
        if name in ('Remap Noise to Scalar', 'Velocity Noise'): add('experimental_noise', name)
        if name in ('Position From Parent Particles', 'Inherit Initial Value From Parent Particle'):
            add('experimental_parent', name)
        if name == 'Color Random' and float(p.get('tint_perc', 0)) != 0:
            add('experimental_tint', 'Color Random samples map lighting')
        if name == 'Position Along Ring' and p.get('even distribution', False):
            add('experimental_spline', 'Evenly distributed ring positions')
    for m in operators:
        name, p = m['function'], m['parameters']
        if name in ('Set child control points from particle positions', 'Inherit Attribute From Parent Particle'):
            add('experimental_parent', name)
        if name == 'Lifespan Decay' and any(float(p.get(k, 0)) != 0 for k in
                ('operator start fadein', 'operator end fadein', 'operator start fadeout', 'operator end fadeout', 'operator fade oscillate')):
            add('experimental_delayed_decay', 'Lifespan Decay has authored strength timing')
    for m in locks:
        p = m['parameters']
        if any(float(p.get(k, 1)) != 1 for k in ('start_fadeout_min', 'start_fadeout_max', 'end_fadeout_min', 'end_fadeout_max')):
            add('experimental_partial_lock', 'Control-point attachment has fade ranges')
    if material:
        if material.get('shader', '').casefold() == 'refract': add('experimental_refraction', 'Refract material shader')
        if material.get('spline_type') == 1: add('experimental_spline', 'SpriteCard spline material')
    return found


def format_report(report, enabled):
    lines = ['PARTICLE OPTION SCAN',
             'Detects authored features, including child effects. Detection does not guarantee that every feature combination converts.',
             'Not detected means absent from resolved definitions; missing assets leave the scan incomplete.', '']
    detected = set()
    for session in report['sessions']:
        lines += ['Session: ' + session['session']]
        for effect in session['effects']:
            lines += ['  ' + effect['system'] + ' / ' + effect['definition']]
            if not effect['options']: lines += ['    No experimental option detected.']
            for key, reasons in effect['options'].items():
                detected.add(key)
                lines += ['    ' + LABELS[key] + (' [ON]' if enabled.get(key) else ' [OFF — consider enabling]') + ': ' + '; '.join(reasons)]
        for error in session['errors']: lines += ['  INCOMPLETE: ' + error]
        if not session['effects'] and not session['errors']: lines += ['  No particle systems found.']
        lines += ['']
    lines += ['Option summary:']
    lines += [LABELS[key] + ': ' + ('DETECTED' if key in detected else 'Not detected in resolved effects') for key in LABELS]
    return '\n'.join(lines), detected
