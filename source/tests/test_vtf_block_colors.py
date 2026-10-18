import importlib.util,struct,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('block_colors',Path(__file__).resolve().parents[1]/'vendor/SourceIO/library/source1/vtf/block_colors.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
rgb=module.rgb

class BlockColorTests(unittest.TestCase):
    def vtf(self,fmt=15,color=0xffff,indices=0,width=4,height=4,minor=2,mips=1,extra=b''):
        h=bytearray(80 if minor<3 else 88)
        struct.pack_into('<4sIII',h,0,b'VTF\0',7,minor,len(h))
        struct.pack_into('<HH',h,16,width,height);struct.pack_into('<H',h,24,1)
        struct.pack_into('<I',h,52,fmt);h[56]=mips
        if minor>=3:
            struct.pack_into('<I',h,68,1);struct.pack_into('<3sBI',h,80,b'\x30\0\0',0,88)
        block=struct.pack('<HHI',color,0,indices)
        if fmt==14:block=b'\xff'*8+block
        if fmt==15:block=b'\xff\xff'+bytes(6)+block
        return bytes(h)+extra+block

    def test_full_range_endpoints_all_compressions(self):
        for fmt in (13,14,15,20):
            for value,expected in [(0xffff,[255,255,255]),(0xf800,[255,0,0]),(0x7e0,[0,255,0]),(31,[0,0,255])]:
                self.assertEqual(rgb(self.vtf(fmt,value))[0,0].tolist(),expected)

    def test_four_color_interpolation(self):
        colors=rgb(self.vtf(indices=0xe4))[0].tolist()
        self.assertEqual(colors,[[255]*3,[0]*3,[170]*3,[85]*3])

    def test_bc1_three_color_mode(self):
        data=bytearray(self.vtf(fmt=13,indices=0xe4));struct.pack_into('<HH',data,80,0,0xffff)
        self.assertEqual(rgb(data)[0].tolist(),[[0]*3,[255]*3,[127]*3,[0]*3])

    def test_bc3_always_four_color_mode(self):
        data=bytearray(self.vtf(indices=0xe4));struct.pack_into('<HH',data,88,0,0xffff)
        self.assertEqual(rgb(data)[0].tolist(),[[0]*3,[255]*3,[85]*3,[170]*3])

    def test_orientation_and_partial_blocks(self):
        image=rgb(self.vtf(indices=0x55555500,width=3,height=2))
        self.assertEqual(image.shape,(2,3,3));self.assertEqual(image[0,0].tolist(),[255]*3);self.assertEqual(image[1,0].tolist(),[0]*3)

    def test_resource_and_mip_offsets(self):
        self.assertEqual(rgb(self.vtf(minor=3))[0,0].tolist(),[255]*3)
        self.assertEqual(rgb(self.vtf(mips=2,extra=bytes(16)))[0,0].tolist(),[255]*3)

    def test_unsupported_uses_existing_native_path(self):
        for offset,value in ((24,2),(20,0x4000),(63,2)):
            data=bytearray(self.vtf());struct.pack_into('<H' if offset!=20 else '<I',data,offset,value)
            self.assertIsNone(rgb(data))
        self.assertIsNone(rgb(self.vtf(fmt=0)))

    def test_truncated_image_rejected(self):
        with self.assertRaises(ValueError):rgb(self.vtf()[:-1])

if __name__=='__main__':unittest.main()
