"""Limited, explicit adapter for Source ``Set Control Point Positions``.

The supported subset places control points at local offsets from the particle
system origin (parent 0).  The offsets follow the animated system transform.
World-space placement, nonzero offset CPs, operator fades, and other parents
remain rejected until their Source 1 behavior is verified.
"""
from __future__ import annotations

import math


_SLOTS = ("First", "Second", "Third", "Fourth")
_FADE_FIELDS = (
    "operator start fadein", "operator end fadein",
    "operator start fadeout", "operator end fadeout",
    "operator fade oscillate",
)
_NEUTRAL_FIELDS = {
    # PCF metadata fields emitted by Source's default operator builder. These
    # values do not alter the local, animated control-point placement below.
    "operator time offset seed": 0,
    "operator time offset min": 0.0,
    "operator time offset max": 0.0,
    "operator time scale seed": 0,
    "operator time scale min": 1.0,
    "operator time scale max": 1.0,
    "operator time strength random scale max": 1.0,
    "operator strength scale seed": 0,
    "operator strength random scale min": 1.0,
    "operator strength random scale max": 1.0,
    "operator strength scale control point": -1,
    "operator end cap state": -1,
    "operator help and notes": "",
    "Inherit CP Orientation": False,
    "Only set position once": False,
}


def _is_neutral(value, expected):
    if isinstance(expected, bool):
        return type(value) is bool and value is expected
    if isinstance(expected, str):
        return type(value) is str and value == expected
    if isinstance(value, bool):
        return False
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(number) and number == expected


def _index(value, label):
    if isinstance(value, bool):
        raise ValueError(f"Invalid {label} control point index")
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"Invalid {label} control point index") from None
    if not math.isfinite(number) or number != int(number) or not 0 <= number < 64:
        raise ValueError(f"Invalid {label} control point index")
    return int(number)


def settings(parameters):
    """Validate and normalize the verified local-origin operator subset."""
    if bool(parameters.get("Set positions in world space", False)):
        raise ValueError("Set Control Point Positions in world space is not yet supported")
    offset_cp = _index(parameters.get("Control Point to offset positions from", 0), "offset")
    if offset_cp != 0:
        raise ValueError("Set Control Point Positions with a nonzero offset control point is not yet supported")
    for field in _FADE_FIELDS:
        value = parameters.get(field, 0.0)
        if not math.isfinite(float(value)) or float(value) != 0.0:
            raise ValueError("Set Control Point Positions operator fades are not yet supported")

    configured = {}
    allowed = {"functionName", "operator enabled", "Set positions in world space",
               "Control Point to offset positions from", *_FADE_FIELDS}
    allowed.update(_NEUTRAL_FIELDS)
    for slot in _SLOTS:
        number_key = f"{slot} Control Point Number"
        parent_key = f"{slot} Control Point Parent"
        location_key = f"{slot} Control Point Location"
        allowed.update((number_key, parent_key, location_key))
        if not any(key in parameters for key in (number_key, parent_key, location_key)):
            continue
        target = _index(parameters.get(number_key, 0), "target")
        parent = _index(parameters.get(parent_key, 0), "parent")
        if parent != 0:
            raise ValueError("Set Control Point Positions with a nonzero parent is not yet supported")
        raw = parameters.get(location_key, (0.0, 0.0, 0.0))
        try:
            location = tuple(float(value) for value in raw)
        except (TypeError, ValueError):
            raise ValueError("Invalid Set Control Point Positions location") from None
        if len(location) != 3 or not all(math.isfinite(value) for value in location):
            raise ValueError("Invalid Set Control Point Positions location")
        row = {"target": target, "parent": parent, "location": location}
        prior = configured.get(target)
        if prior is not None and prior != row:
            raise ValueError(f"Set Control Point Positions configures control point {target} more than once")
        configured[target] = row
    unknown = set(parameters) - allowed
    if unknown:
        raise ValueError("Unverified Set Control Point Positions fields: " + ", ".join(sorted(unknown)))
    nonneutral = [key for key, expected in _NEUTRAL_FIELDS.items()
                  if key in parameters and not _is_neutral(parameters[key], expected)]
    if nonneutral:
        raise ValueError("Set Control Point Positions has non-default unverified fields: " + ", ".join(sorted(nonneutral)))
    if not configured:
        raise ValueError("Set Control Point Positions has no configured control points")
    return {"points": [configured[index] for index in sorted(configured)],
            "offset_control_point": 0, "world_space": False,
            "limitations": [
                "Local offsets follow the imported particle-system origin transform.",
                "Source 1 particle-tick parity and rendered visual parity are unverified.",
            ]}


class _ControlPointView:
    """Read-only CP transform facade evaluated at the current Blender frame."""
    def __init__(self, name, base, location, scale, scene=None):
        self.name = name
        self._base = base
        self._location = tuple(float(value) * scale for value in location)
        self._scene = scene

    @property
    def parent(self):
        # Expose the transform dependency so static-transform checks fail
        # closed when the particle system origin is animated.
        return self._base

    @property
    def matrix_world(self):
        from mathutils import Matrix, Vector
        if self._scene is None:
            base = self._base.matrix_world
        else:
            # SFM control transforms may be driven by constraints or actions.
            # Read the evaluated transform after frame_set(), not the original
            # datablock matrix, so the virtual CP follows those drivers too.
            depsgraph = self._scene.view_layers[0].depsgraph
            base = self._base.evaluated_get(depsgraph).matrix_world
        return base @ Matrix.Translation(Vector(self._location))

    def evaluated_get(self, _depsgraph):
        return self


def overlay(definition, descriptor, control_objects, scale, scene=None):
    """Return a per-definition CP mapping with validated virtual CP transforms.

    The original imported objects are never modified.  Each view computes its
    matrix lazily, so existing particle sampling calls follow scene.frame_set.
    """
    modules = [module for module in definition.get("modules", {}).get("operators", [])
               if module.get("function", "").casefold() == "set control point positions"
               and module.get("parameters", {}).get("operator enabled", True)]
    if not modules:
        return control_objects, None
    if len(modules) != 1:
        raise ValueError("Repeated Set Control Point Positions operators are not yet supported")
    config = settings(modules[0].get("parameters", {}))
    points = descriptor.get("control_points", [])
    if not isinstance(points, list):
        points = list(points) if isinstance(points, tuple) else ([] if points is None else [points])
        descriptor["control_points"] = points
    if not points:
        raise ValueError("Set Control Point Positions requires an imported system origin")
    origin_id = points[0].get("id")
    origin = control_objects.get(origin_id)
    if origin is None:
        raise ValueError("Set Control Point Positions system origin has no imported transform")
    result = dict(control_objects)
    for point in config["points"]:
        target = point["target"]
        while target >= len(points):
            index = len(points)
            identity = f"{origin_id}:set-control-point:{index}"
            points.append({"id": identity, "name": f"controlPoint{index}",
                           "type": "DmeTransform", "generated_by": "Set Control Point Positions"})
        identity = points[target].get("id")
        result[identity] = _ControlPointView(
            f"{definition.get('name', 'particle')} CP{target}", origin,
            point["location"], scale, scene)
    return result, config
