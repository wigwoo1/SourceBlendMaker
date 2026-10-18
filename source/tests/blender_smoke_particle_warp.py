"""Run with Blender: blender --background --python tests/blender_smoke_particle_warp.py"""
import sys
from pathlib import Path

APP=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(APP))

from mathutils import Matrix
from particle_warp import apply_birth

rotation_matrix=Matrix.Rotation(1.5707963267948966,3,'Z')
rotation=tuple(tuple(float(rotation_matrix[row][column]) for column in range(3)) for row in range(3))
installed_fire_jet_warp={'function':'Position Modify Warp Random','parameters':{
    'warp min':[.20000000298,.20000000298,.20000000298],
    'warp transition time (treats min/max as start/end sizes)':2.0}}
position,offset,velocity=apply_birth((0.,2.,0.),(0.,1.,0.),(0.,3.,0.),
    [installed_fire_jet_warp],1.0,lambda cp:((0.,0.,0.),rotation),None)
expected=((0.,1.2,0.),(0.,.6,0.),(0.,1.8,0.))
for result,reference in zip((position,offset,velocity),expected):
    if any(abs(actual-target)>1e-5 for actual,target in zip(result,reference)):
        raise AssertionError(f'Warp mismatch: {result!r} != {reference!r}')
print('BLENDER_WARP_INTEGRATION_OK',position,offset,velocity)
