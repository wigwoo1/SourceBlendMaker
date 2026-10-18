"""Frame selection helpers for the particle geometry bake."""


def samples(frames,seconds,step=1):
    """Return sampled particle frames and the next sample boundary per frame.

    The terminal session frame is always retained so a sampled bake preserves
    the authored end pose. Between selected frames, the most recent sprite
    geometry is held until the next selected frame.
    """
    if len(frames)!=len(seconds):raise ValueError('Particle frames and times must have equal lengths')
    try:step=int(step)
    except (TypeError,ValueError):raise ValueError('Particle frame sampling must be 1, 2, 4 or 8')
    if step not in (1,2,4,8):raise ValueError('Particle frame sampling must be 1, 2, 4 or 8')
    indices=list(range(0,len(frames),step))
    if len(frames) and indices[-1]!=len(frames)-1:indices.append(len(frames)-1)
    sampled_frames=[frames[index] for index in indices]
    sampled_seconds=[seconds[index] for index in indices]
    next_frames={int(frame):(int(sampled_frames[i+1]) if i+1<len(sampled_frames) else int(frame)+1)
                 for i,frame in enumerate(sampled_frames)}
    return sampled_frames,sampled_seconds,next_frames
