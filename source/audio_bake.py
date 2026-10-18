"""Bake Source audio playback into portable PCM using Blender's decoder."""
import wave
import numpy as np


def bake(path,target,offset,duration,clock_rate,pitches,fps):
    import aud
    source=aud.Sound(str(path)).cache()
    sample_rate,channels=source.specs
    samples=source.data()
    if len(samples)<2:raise ValueError('Sound has fewer than two decoded samples')
    sample_rate=int(sample_rate);channels=int(channels)
    pitches=np.asarray(pitches,dtype=float)/100.
    if not np.isfinite(pitches).all() or np.any(pitches<=0):raise ValueError('Sound pitch must be positive and finite')
    if not np.isfinite(clock_rate) or abs(clock_rate)<1e-10:raise ValueError('Sound time scale must be nonzero')
    # Integrate piecewise-linear pitch in timeline seconds, then map to source
    # time. This preserves offsets and supports reversed clip clocks as well.
    cumulative=np.concatenate(([0.],np.cumsum((pitches[:-1]+pitches[1:])*.5/fps)))
    count=max(1,round(duration*sample_rate))
    target.parent.mkdir(parents=True,exist_ok=True)
    with wave.open(str(target),'wb') as stream:
        stream.setnchannels(channels);stream.setsampwidth(4);stream.setframerate(sample_rate)
        for first in range(0,count,262144):
            timeline=np.arange(first,min(count,first+262144),dtype=float)/sample_rate
            frame=timeline*fps;index=np.minimum(frame.astype(int),len(pitches)-2);fraction=frame-index
            phase=cumulative[index]+(pitches[index]*fraction+(pitches[index+1]-pitches[index])*fraction*fraction*.5)/fps
            cursor=(offset+phase/clock_rate)*sample_rate
            lower=np.floor(cursor).astype(np.int64);weight=cursor-lower
            valid=(lower>=0)&(lower<len(samples)-1)
            safe=np.clip(lower,0,max(0,len(samples)-2))
            output=samples[safe]*(1-weight[:,None])+samples[safe+1]*weight[:,None]
            output[~valid]=0
            stream.writeframes((np.clip(output,-1,1)*2147483647).astype('<i4').tobytes())
    return target
