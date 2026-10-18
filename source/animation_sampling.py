"""Keyframe reduction helpers for dense sampled animation curves."""
from __future__ import annotations

import bisect
import math


def parse_target_fps(value):
    """Return 0 (keep all keys) or a valid requested animation key rate."""
    try:
        rate = float(value)
    except (TypeError, ValueError):
        raise ValueError('Animation keyframe rate must be 0 (keep all keys) or between 1 and 240 FPS.')
    if not math.isfinite(rate) or rate < 0 or rate > 240:
        raise ValueError('Animation keyframe rate must be 0 (keep all keys) or between 1 and 240 FPS.')
    return rate


def resample_curve(frames, values, source_fps, target_fps):
    """Resample a linear curve at target_fps, retaining its exact endpoints.

    Frame coordinates may be fractional (for example, a 24 FPS key rate on a
    60 FPS timeline). Values between retained samples are linearly interpolated.
    """
    source_frames = [float(frame) for frame in frames]
    source_values = [float(value) for value in values]
    if len(source_frames) != len(source_values):
        raise ValueError('Animation frames and values must have the same length.')
    source_fps = float(source_fps or 0)
    target_fps = parse_target_fps(target_fps)
    if (len(source_frames) <= 2 or source_fps <= 0 or target_fps <= 0
            or target_fps >= source_fps):
        return source_frames, source_values

    first, last = source_frames[0], source_frames[-1]
    step = source_fps / target_fps
    count = int(math.floor((last - first) / step + 1e-10))
    sampled_frames = [first + index * step for index in range(count + 1)]
    if not sampled_frames or last - sampled_frames[-1] > 1e-7:
        sampled_frames.append(last)
    else:
        sampled_frames[-1] = last

    sampled_values = []
    for frame in sampled_frames:
        right = bisect.bisect_right(source_frames, frame)
        if right == 0:
            sampled_values.append(source_values[0])
        elif right >= len(source_frames):
            sampled_values.append(source_values[-1])
        else:
            left = right - 1
            span = source_frames[right] - source_frames[left]
            if span <= 0:
                sampled_values.append(source_values[right])
            else:
                amount = (frame - source_frames[left]) / span
                sampled_values.append(source_values[left] * (1 - amount) + source_values[right] * amount)
    return sampled_frames, sampled_values
