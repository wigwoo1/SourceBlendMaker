import sys,io,unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import datamodel
from particles import Definitions

class ParticleFileHintTests(unittest.TestCase):
    def test_old_absolute_hint_loads_from_selected_mount_without_global_scan(self):
        dm=datamodel.DataModel('pcf',1);root=dm.add_element('root');effect=dm.add_element('fire')
        root['particleSystemDefinitions']=datamodel.make_array([effect],datamodel.Element)
        raw=dm.echo('keyvalues2',1).encode();requests=[]
        class Mounts:
            def glob(self,pattern):raise AssertionError('Moved hint should resolve without global scan')
        def buffer(path):
            requests.append(path)
            return io.BytesIO(raw) if path=='particles/custom/fire.pcf' else None
        assets=SimpleNamespace(cm=Mounts(),buffer=buffer)
        session=datamodel.DataModel('sfm',1);system=session.add_element('fire1','DmeParticleSystem');system['particleSystemType']='fire'
        result=Definitions(assets).describe(system,[r'D:\OldSFM\game\workshop\particles\custom\fire.pcf'])
        self.assertEqual(requests,['particles/custom/fire.pcf'])
        self.assertEqual(result['pcf'],'particles/custom/fire.pcf')
        self.assertEqual(result['recorded_pcf_files'],[{'path':'particles/custom/fire.pcf','parsed':True}])
    def test_failed_hint_is_reused_with_the_same_diagnostic(self):
        dm=datamodel.DataModel('sfm',1)
        system=dm.add_element('fire1','DmeParticleSystem')
        system['particleSystemDefinition']=dm.add_element('embedded_fire')
        for raw in (None,b'invalid particle data'):
            calls=[]
            def buffer(path):
                calls.append(path)
                return io.BytesIO(raw) if raw is not None else None
            definitions=Definitions(SimpleNamespace(buffer=buffer))
            first=definitions.describe(system,['missing.pcf'])
            second=definitions.describe(system,['missing.pcf'])
            self.assertEqual(calls,['missing.pcf'])
            self.assertEqual(first['recorded_pcf_files'],second['recorded_pcf_files'])
            self.assertFalse(first['recorded_pcf_files'][0]['parsed'])
            first['recorded_pcf_files'][0]['reason']='caller mutation'
            self.assertNotEqual(definitions.describe(system,['missing.pcf'])['recorded_pcf_files'][0]['reason'],'caller mutation')

    def test_recorded_pcf_is_loaded_before_glob(self):
        dm=datamodel.DataModel('pcf',1);root=dm.add_element('root');effect=dm.add_element('fire')
        root['particleSystemDefinitions']=datamodel.make_array([effect],datamodel.Element)
        raw=dm.echo('keyvalues2',1).encode()
        class Mounts:
            def glob(self,pattern):raise AssertionError('Recorded definition should avoid a global scan')
        assets=SimpleNamespace(cm=Mounts(),buffer=lambda path:io.BytesIO(raw) if path=='custom/fire.pcf' else None)
        session=datamodel.DataModel('sfm',1);system=session.add_element('fire1','DmeParticleSystem');system['particleSystemType']='fire'
        result=Definitions(assets).describe(system,['custom\\fire.pcf'])
        self.assertEqual(result['pcf'],'custom/fire.pcf')
        self.assertIn('custom/fire.pcf',result['dependencies'])
        self.assertEqual(result['recorded_pcf_files'],[{'path':'custom/fire.pcf','parsed':True}])

if __name__=='__main__':unittest.main()
