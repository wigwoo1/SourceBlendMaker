import sys,unittest,struct
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from particle_sheet import parse_resource,parse_vtf,coordinates,animation_rate

class SheetTests(unittest.TestCase):
    def test_invalid_animation_rate_rejected(self):
        for rate in (-1,float('nan'),float('inf')):
            with self.assertRaises(ValueError):animation_rate({'animation rate':rate})
        self.assertEqual(animation_rate({'animation rate':0}),0)

    def resource(self,version=0,clamp=0):
        data=struct.pack('<II',version,1)+struct.pack('<IIIf',2,clamp,2,2.)
        for rectangle in ((0,0,.5,1),(.5,0,1,1)):
            data+=struct.pack('<f',1)+struct.pack('<4f',*rectangle)*(1 if version==0 else 4)
        return data

    def test_vtf_dictionary_finds_particle_metadata(self):
        resource=self.resource(1);header=bytearray(88)
        struct.pack_into('<4sIII',header,0,b'VTF\0',7,3,88)
        struct.pack_into('<I',header,68,1);struct.pack_into('<3sBI',header,80,b'\x10\0\0',0,88)
        sheet=parse_vtf(bytes(header)+struct.pack('<I',len(resource))+resource)
        self.assertEqual(len(sheet['2']['frames']),2)
        self.assertEqual(len(sheet['2']['frames'][0]['coordinates']),4)

    def test_sequence_progress_and_wrapping(self):
        sheet=parse_resource(self.resource())
        self.assertEqual(coordinates(sheet,2,.25,10,{'animation rate':1})[0],(0,0))
        self.assertEqual(coordinates(sheet,2,.75,10,{'animation rate':1})[0],(.5,0))
        self.assertEqual(coordinates(sheet,2,1.25,10,{'animation rate':1})[0],(0,0))
        self.assertEqual(coordinates(sheet,2,100,10,{'animation_fit_lifetime':True})[0],(0,0))
        diagnostics=[]
        self.assertEqual(coordinates(sheet,1,.25,10,{'animation rate':1},diagnostics)[0],(0,0))
        self.assertEqual(diagnostics,['Particle requested missing texture sequence 1; used sole available sequence 2'])
        # Outside the known sequence range, clamp to its nearest boundary and
        # report the approximation. An internal missing sequence stays ambiguous.
        multi={'0':sheet['2'],'2':sheet['2']}
        diagnostics=[]
        self.assertEqual(coordinates(multi,-1,.25,10,{},diagnostics)[0],(0,0))
        self.assertEqual(diagnostics,['Particle requested out-of-range texture sequence -1; clamped to boundary sequence 0'])
        diagnostics=[]
        self.assertEqual(coordinates(multi,3,.25,10,{},diagnostics)[0],(0,0))
        self.assertEqual(diagnostics,['Particle requested out-of-range texture sequence 3; clamped to boundary sequence 2'])
        with self.assertRaisesRegex(ValueError,'no sequence'):coordinates(multi,1,1,1,{})

    def test_clamp_and_fps(self):
        sheet=parse_resource(self.resource(clamp=1))
        self.assertEqual(coordinates(sheet,2,100,1,{})[0],(.5,0))
        self.assertEqual(coordinates(sheet,2,.25,1,{'animation rate':4,'use animation rate as FPS':True})[0],(.5,0))

    def test_rejects_truncation_and_unknown_version(self):
        with self.assertRaises(ValueError):parse_resource(self.resource()[:-1])
        with self.assertRaises(ValueError):parse_resource(struct.pack('<II',3,0))
        with self.assertRaises(ValueError):parse_vtf(b'not a VTF')

    def test_duplicate_sequence_keeps_last_and_flags_ambiguity(self):
        entry=self.resource()[8:];data=struct.pack('<II',0,2)+entry+entry
        self.assertEqual(parse_resource(data)['2']['duplicate_definitions'],1)
