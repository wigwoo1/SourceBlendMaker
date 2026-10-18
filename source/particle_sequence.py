"""Sequence context ordering from installed SFM; converter RNG is approximate."""
import math

class SequenceSelection:
    def __init__(self,parameters,rng):
        self.rng=rng
        bounds=[parameters.get(key,0) for key in ('sequence_min','sequence_max')]
        if any(isinstance(value,bool) or not math.isfinite(float(value)) or float(value)!=int(value) for value in bounds):
            raise ValueError('Sequence bounds must be finite integers')
        self.minimum,self.maximum=map(int,bounds)
        if not all(0<=value<64 for value in (self.minimum,self.maximum)):
            raise ValueError('Sequence endpoints must be within 0..63')
        self.shuffle=bool(parameters.get('shuffle',False));self.linear=bool(parameters.get('linear',False))
        if self.minimum>self.maximum and (self.shuffle or self.linear):
            raise ValueError('Reversed shuffle/linear sequence contexts remain unverified')
        self.values=list(range(self.minimum,self.maximum+1));self.cursor=0
        if self.shuffle:self._shuffle()
    def _shuffle(self):
        for end in range(len(self.values)-1,0,-1):
            selected=int((end+1)*self.rng.random())
            self.values[end],self.values[selected]=self.values[selected],self.values[end]
    def next(self):
        if not (self.shuffle or self.linear):
            # Primary random branch 0x10235aa9..0x10235af4 uses the same signed
            # span / float32 multiply / truncation as Sequence Two Random.
            # In particular, authored 3..0 produces 3 or 2, not a sorted 0..3.
            from particle_secondary_sequence import from_unit
            return int(from_unit({'sequence_min':self.minimum,'sequence_max':self.maximum},self.rng.random()))
        if self.cursor==len(self.values):
            if self.shuffle:self._shuffle()
            self.cursor=0
        value=self.values[self.cursor];self.cursor+=1
        return value
