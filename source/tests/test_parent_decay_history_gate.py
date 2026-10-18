import unittest
from particle_decay_experimental import requires_extended_history

class ParentDecayHistoryGateTests(unittest.TestCase):
    def test_default_decay_does_not_require_extended_parent_history(self):
        module={'function':'Lifespan Decay','parameters':{}}
        self.assertFalse(requires_extended_history([module],True))
        module['parameters']={'operator start fadein':2,'operator end fadein':2}
        self.assertTrue(requires_extended_history([module],True))
        self.assertFalse(requires_extended_history([module],False))
        module['parameters']['operator enabled']=False
        self.assertFalse(requires_extended_history([module],True))
