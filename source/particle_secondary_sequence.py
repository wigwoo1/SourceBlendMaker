"""Decoded Sequence Two Random birth arithmetic for supported SpriteCards.

The installed initializer writes field 13, independently of sequence field 9.
Its two-sequence shader/UV pipeline has explicit renderer/material support gates.
Source collection RNG counters and seeds are not reproduced by this helper.
"""
import math
import struct

FIELD = 13


def _float32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def bounds(parameters):
    values = [parameters.get(k, 0) for k in ('sequence_min', 'sequence_max')]
    if any(isinstance(v, bool) or not math.isfinite(float(v)) or float(v) != int(v)
           or not 0 <= int(v) < 64 for v in values):
        raise ValueError('Secondary sequence bounds require integers within 0..63')
    # Authored reversed bounds exist. The installed instruction stream uses
    # (max-min+1), signed truncation and addition without sorting the bounds.
    return tuple(map(int, values))


def from_unit(parameters, unit):
    minimum, maximum = bounds(parameters)
    unit = float(unit)
    if not math.isfinite(unit) or not 0 <= unit < 1:
        raise ValueError('Secondary sequence random input must be within [0,1)')
    product = _float32(_float32(maximum - minimum + 1) * _float32(unit))
    return _float32(minimum + math.trunc(product))


def sample(parameters, rng):
    # Source consumes a table sample even for equal bounds. Keep consumption
    # explicit; callers may supply decoded table values for arithmetic checks.
    return from_unit(parameters, rng.random())


def initialize(modules, fields, rng):
    result = dict(fields)
    for module in modules:
        if module['function'] == 'Sequence Two Random' and module['parameters'].get('operator enabled', True):
            result[FIELD] = sample(module['parameters'], rng)
    return result
