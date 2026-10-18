import tempfile,unittest
from pathlib import Path
from batch_queue import folder_sessions,plan_jobs

class FolderQueueTests(unittest.TestCase):
    def test_folder_filter_order_and_output_collision(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name in ('z.DMX','Alpha.dmx','notes.txt'):(root/name).write_text('')
            (root/'nested').mkdir();(root/'nested'/'other.dmx').write_text('')
            sessions=folder_sessions(root)
            self.assertEqual([Path(p).name for p in sessions],['Alpha.dmx','z.DMX'])
            (root/'Alpha.blend').write_text('existing')
            jobs=plan_jobs(sessions,{},root)
            self.assertEqual([Path(j['output']).name for j in jobs],['Alpha (2).blend','z.blend'])
    def test_empty_folder(self):
        with tempfile.TemporaryDirectory() as tmp:self.assertEqual(folder_sessions(tmp),[])
