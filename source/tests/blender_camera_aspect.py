"""Run with Blender --background --python-exit-code 1 --python this_file.

Checks the Source 4:3 FOV reference with animated native cameras. No SFM assets
are needed. Does not establish visual parity with an SFM render.
"""
import math
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from blender_worker import import_camera


class CameraElement(dict):
    name = 'Aspect fixture'


class Shot:
    element = SimpleNamespace(name='Fixture shot')

    def value(self, element, attribute, time, default):
        return 30 + time * 30 if attribute == 'fieldOfView' else default


bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.camera = import_camera(Shot(), CameraElement(), [1, 2, 3], [0, 1, 2])
with tempfile.TemporaryDirectory() as directory:
    path = str(Path(directory) / 'camera.blend')
    bpy.ops.wm.save_as_mainfile(filepath=path)
    bpy.ops.wm.open_mainfile(filepath=path)
    scene = bpy.context.scene
    for width, height, px, py in ((1920, 1080, 1, 1), (800, 600, 1, 1), (600, 800, 1, 1), (720, 480, 1.2, 1)):
        for frame, fov in ((1, 30), (2, 60), (3, 90)):
            scene.frame_set(frame)
            graph = bpy.context.evaluated_depsgraph_get()
            camera = scene.camera.evaluated_get(graph)
            matrix = camera.calc_matrix_camera(graph, x=width, y=height, scale_x=px, scale_y=py)
            cot = 1 / math.tan(math.radians(fov) / 2)
            aspect = width * px / (height * py)
            assert abs(matrix[0][0] - cot * (4 / 3) / aspect) < 1e-5
            assert abs(matrix[1][1] - cot * (4 / 3)) < 1e-5
print('NATIVE CAMERA ASPECT REGRESSION PASSED')
