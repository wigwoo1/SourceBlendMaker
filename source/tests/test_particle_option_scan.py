import unittest
from particle_option_scan import detect,format_report,LABELS


def definition(**groups):
    return {'modules': {g: [{'function': n, 'parameters': p} for n,p in items] for g,items in groups.items()}}


class ParticleOptionScanTests(unittest.TestCase):
    def test_disabled_modules_and_plain_lifespan_do_not_recommend_options(self):
        d=definition(initializers=[('Velocity Noise',{'operator enabled':False})],operators=[('Lifespan Decay',{})])
        self.assertEqual(detect(d),{})

    def test_all_options_and_combination_dependencies(self):
        d=definition(initializers=[('Velocity Noise',{}),('Position From Parent Particles',{}),('Color Random',{'tint_perc':.5})],
            forces=[('Pull towards control point',{})],operators=[('Movement Lock to Control Point',{'end_fadeout_min':.5}),('Lifespan Decay',{'operator start fadein':.2})])
        self.assertEqual(set(detect(d,{'shader':'Refract','spline_type':1})),set(LABELS))

    def test_twist_lock_does_not_require_pull_option(self):
        found=detect(definition(forces=[('twist around axis',{})],operators=[('Movement Lock to Control Point',{})]))
        self.assertEqual(set(found),{'experimental_pull_lock'})

    def test_report_keeps_missing_asset_warning_and_current_setting(self):
        report={'sessions':[{'session':'one.dmx','effects':[{'system':'parent','definition':'child','options':{'experimental_noise':['Velocity Noise']}}],'errors':['Missing VMT']}]}
        text,keys=format_report(report,{'experimental_noise':False})
        self.assertIn('OFF',text);self.assertIn('INCOMPLETE: Missing VMT',text)
        self.assertEqual(keys,{'experimental_noise'})

    def test_empty_session_and_nonmatching_material(self):
        self.assertEqual(detect(definition(),{'shader':'SpriteCard','spline_type':0}),{})
        text,keys=format_report({'sessions':[{'session':'empty.dmx','effects':[],'errors':[]}]},{})
        self.assertIn('No particle systems found',text);self.assertFalse(keys)
