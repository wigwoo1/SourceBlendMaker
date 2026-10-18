"""Analytic approximation of simple scalar particle oscillation.

Integrates sinusoidal attribute velocity from birth; Source tick order and
phase are not reproduced exactly.
"""
import math


def delta(parameters, age):
    multiplier=float(parameters.get('oscillation multiplier',2))
    omega=float(parameters.get('oscillation frequency',1))*multiplier
    phase=float(parameters.get('oscillation start phase',.5))*multiplier
    rate=float(parameters.get('oscillation rate',0))
    return rate*(math.cos(phase)-math.cos(phase+omega*age))/omega if abs(omega)>1e-8 else rate*math.sin(phase)*age


def trail_duration(definition, initial, age):
    value=initial
    for module in definition['modules']['operators']:
        p=module['parameters']
        if module['function']=='Oscillate Scalar Simple' and p.get('operator enabled',True) and int(p.get('oscillation field',7))==10:
            value=max(0.,value+delta(p,age))
    return value
