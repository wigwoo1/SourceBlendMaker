"""Estimate sprite-trail displacement when sampled particle history is static."""
import math


def displacement(observed, velocity, duration, epsilon=1e-9):
    """Return observed motion, or a velocity-based lookback for a static trail.

    Source trails can be authored from an initial velocity without a Movement
    Basic operator. In that case this converter's position evaluator has no
    displacement history to measure, so use velocity times the visible trail
    age as an explicitly approximate fallback.
    """
    observed=tuple(float(v) for v in observed)
    velocity=tuple(float(v) for v in velocity)
    if len(observed)!=3 or len(velocity)!=3:
        raise ValueError('Trail displacement and velocity must be 3D vectors')
    if not all(math.isfinite(v) for v in (*observed,*velocity)):
        raise ValueError('Trail displacement and velocity must be finite')
    duration=float(duration)
    if not math.isfinite(duration) or duration<0:
        raise ValueError('Trail lookback duration must be finite and nonnegative')
    if math.sqrt(sum(v*v for v in observed))>epsilon:
        return observed,False
    estimated=tuple(v*duration for v in velocity)
    if math.sqrt(sum(v*v for v in estimated))<=epsilon:
        return observed,False
    return estimated,True
