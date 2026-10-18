import io,json,tempfile,unittest,zipfile
from pathlib import Path
from project_pack import create_bundle,explicit_reference

class Provider:
    def glob(self,pattern):
        if pattern=='particles/*':yield 'particles/fire.pcf',io.BytesIO(b'fixture particle data')

class RelocatedBundleTests(unittest.TestCase):
    def test_manifest_checks_relocated_particle_reference_against_packed_file(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);session=root/'session.dmx';session.write_bytes(b'fixture session')
            output=root/'bundle.zip'
            references=[explicit_reference('particleFiles',r'D:\OldSFM\game\workshop\particles\fire.pcf'),explicit_reference('particleFiles',r'D:\OldSFM\game\workshop\particles\missing.pcf')]
            result=create_bundle(session,[Provider()],output,references=references)
            self.assertFalse(result['errors'])
            with zipfile.ZipFile(output) as archive:
                self.assertIsNone(archive.testzip())
                self.assertEqual(archive.read('SourceProject/particles/fire.pcf'),b'fixture particle data')
                manifest=json.loads(archive.read('manifest.json'))
                self.assertEqual(manifest['missing_explicit_session_paths'],['particles/missing.pcf'])
                self.assertEqual(archive.read('SourceProject/session.dmx'),session.read_bytes())
