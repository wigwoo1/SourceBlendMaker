import unittest
from particle_maintained_route import native_velocity_noise


def definition(*modules):
    return {'modules':{'initializers':[{'function':name,'parameters':parameters} for name,parameters in modules]}}


class MaintainedRouteTests(unittest.TestCase):
    def test_velocity_noise_uses_existing_maintained_lifecycle(self):
        self.assertTrue(native_velocity_noise(definition(('Velocity Noise',{}),('Lifetime Random',{}))))
    def test_scalar_noise_lifetime_must_not_be_silently_dropped(self):
        self.assertFalse(native_velocity_noise(definition(('Velocity Noise',{}),('Remap Noise to Scalar',{'output field':1}))))
    def test_no_noise_and_disabled_noise_leave_shared_route(self):
        self.assertFalse(native_velocity_noise(definition(('Velocity Noise',{'operator enabled':False}))))
        self.assertFalse(native_velocity_noise(definition(('Radius Random',{}))))
