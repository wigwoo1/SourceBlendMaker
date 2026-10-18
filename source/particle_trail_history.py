"""Map a trail's simulation-age lookback to the authored scene clock."""
from particle_sim import simulation_at


def previous_time(segments, birth, current_time, age, duration):
    previous_age = max(0., age - max(0., duration))
    if previous_age == 0.:
        return birth.time
    if previous_age >= age:
        return current_time
    target = birth.simulation_time + previous_age
    low, high = birth.time, current_time
    for _ in range(50):
        middle = (low + high) * .5
        if simulation_at(segments, middle) < target:
            low = middle
        else:
            high = middle
    return (low + high) * .5
