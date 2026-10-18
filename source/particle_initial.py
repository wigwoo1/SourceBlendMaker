"""Initial particles at collection creation; Source tick/RNG parity unverified."""
import math
from particle_sim import Birth
from particle_sim import simulation_at


def validate_count(value):
    number = float(value)
    if not math.isfinite(number) or number != int(number) or not 0 <= number <= 100000:
        raise ValueError('Initial particle count must be an integer from 0 to 100000')
    return int(number)


def prepend(births, count, creation_time):
    count = validate_count(count)
    if not math.isfinite(creation_time):
        raise ValueError('Invalid initial particle creation time')
    if any(b.time < creation_time for b in births):
        raise ValueError('Emitter birth precedes particle collection creation')
    return ([Birth(i, creation_time, 0.) for i in range(count)] +
            [Birth(i + count, b.time, b.simulation_time) for i, b in enumerate(births)])


def creation_time(segments, delay):
    """Invert the parent simulation clock, including pauses and speed ramps."""
    delay = float(delay)
    if not math.isfinite(delay) or delay < 0:
        raise ValueError('Invalid initial particle child delay')
    if not segments:
        return None
    if delay == 0:
        return segments[0].start
    if simulation_at(segments, segments[-1].end) < delay:
        return None
    low, high = segments[0].start, segments[-1].end
    for _ in range(60):
        middle = (low + high) * .5
        if simulation_at(segments, middle) < delay:
            low = middle
        else:
            high = middle
    return high
