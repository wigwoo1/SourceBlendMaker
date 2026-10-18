"""Position math decoded from installed SpriteCard VS2.0 dynamic modes 0..2.

RNG, float32 shader trig, screen-size fades and visual parity are unverified.
Normal-directed sprites and authored orientation matrices remain explicit gaps.
"""
import math

SHADER_CORNERS = ((1, 0), (0, 0), (0, 1), (1, 1))


def settings(material, renderer):
    if renderer != 'render_animated_sprites' or str(material.get('sfm_particle_shader', '')).lower() != 'spritecard':
        return None
    if material.get('sfm_particle_material_spline_type', 0):
        raise ValueError('Spline SpriteCard material requires the rope renderer')
    value = float(material.get('sfm_particle_material_orientation', 0))
    if not math.isfinite(value) or value != int(value):
        raise ValueError('Invalid SpriteCard material orientation')
    mode = max(0, min(3, int(value)))
    if mode == 3:
        raise ValueError('Normal-directed SpriteCard geometry requires particle normal history')
    matrix = str(material.get('sfm_particle_material_orientation_matrix', '')).strip()
    if mode == 2 and matrix and matrix.casefold() != 'center .5 .5 scale 1 1 rotate 0 translate 0 0':
        raise ValueError('Authored SpriteCard orientation matrix requires verified matrix conversion')
    return {'orientation': mode, 'orientation_source': 'SpriteCard material $orientation',
            'orientation_matrix': 'identity' if mode == 2 else None}


def corners(center, radius, roll, yaw, orientation, eye,
            basis=((1, 0, 0), (0, 1, 0), (0, 0, 1))):
    if orientation not in (0, 1, 2):
        raise ValueError('Normal-directed SpriteCard geometry requires particle normal history')
    if (len(center) != 3 or len(eye) != 3 or len(basis) != 3
            or any(len(row) != 3 for row in basis)
            or not all(math.isfinite(float(v)) for v in
                       (*center, radius, roll, yaw, *eye, *(v for row in basis for v in row)))):
        raise ValueError('Invalid SpriteCard geometry inputs')
    cr, sr, cy, sy = math.cos(roll), math.sin(roll), math.cos(yaw), math.sin(yaw)
    if orientation == 1:
        dx, dy = center[0] - eye[0], center[1] - eye[1]
        length = math.hypot(dx, dy)
        if length <= 1e-12:
            raise ValueError('Degenerate horizontal SpriteCard view')
        rx, ry = -dy / length, dx / length
        right = (cy * rx + sy * ry, cy * ry - sy * rx, 0)
    result = []
    # PET's packed UV lerp reverses both endpoints. This permutation agrees
    # with particle_sheet.coordinates' Blender bottom-left-first UV order.
    for u, v in SHADER_CORNERS:
        x, y = 2 * u - 1, 2 * v - 1
        a, b = cr * x + sr * y, cr * y - sr * x
        if orientation == 0:
            local = (-cy * a, b, sy * a)
            offset = tuple(sum(local[j] * basis[j][i] for j in range(3)) for i in range(3))
        elif orientation == 1:
            offset = (a * right[0], a * right[1], b)
        else:
            offset = (b, a, 0)
        result.append(tuple(p + radius * q for p, q in zip(center, offset)))
    return tuple(result)
