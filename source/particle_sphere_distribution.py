"""Approximate selection for Position Within Sphere Random's supplied CP range."""
import math


def settings(parameters, highest_control_point=None):
    if parameters.get("create in model", 0):
        raise ValueError("Position Within Sphere Random model placement is not yet supported")
    enabled = parameters.get("randomly distribute to highest supplied Control Point", False)
    if type(enabled) is not bool:
        raise ValueError("Invalid highest-control-point distribution flag")
    if not enabled:
        return None
    raw_start = parameters.get("control_point_number", 0)
    if isinstance(raw_start, bool):
        raise ValueError("Invalid sphere-distribution starting control point")
    start = float(raw_start)
    if not math.isfinite(start) or start != int(start) or not 0 <= start < 64:
        raise ValueError("Invalid sphere-distribution starting control point")
    highest = None
    if highest_control_point is not None:
        if isinstance(highest_control_point, bool) or not 0 <= int(highest_control_point) < 64:
            raise ValueError("Invalid highest supplied control point")
        highest = int(highest_control_point)
        if highest < start:
            raise ValueError("Highest supplied control point precedes the distribution start")
    growth = float(parameters.get("randomly distribution growth time", 0.0))
    if not math.isfinite(growth) or growth != 0.0:
        raise ValueError("Nonzero control-point distribution growth time is not yet supported")
    scale_cp = float(parameters.get("scale cp (distance/speed/local speed)", -1))
    if not math.isfinite(scale_cp) or scale_cp != -1.0:
        raise ValueError("Control-point-scaled sphere distribution is not yet supported")
    return {"start": int(start), "highest": highest, "growth_time": growth}


def choose(rng, configuration):
    if configuration is None or configuration["highest"] is None:
        raise ValueError("A validated control-point distribution is required")
    return rng.randint(configuration["start"], configuration["highest"])
