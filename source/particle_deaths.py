"""Irreversible per-collection death times, separate from authored lifetime.

This stores simulator decisions; it does not infer crossings or engine ticks.
The caller must advance its simulation before querying a newly reached time.
"""
import math


class Deaths:
    def __init__(self):
        self._times={};self._births={};self._events=[]

    def register(self,identity,birth_time):
        if type(identity) is not int or identity<0:
            raise ValueError('Nonnegative integer particle identity required')
        if not math.isfinite(float(birth_time)):
            raise ValueError('Finite particle birth time required')
        born=float(birth_time)
        if identity in self._births and self._births[identity]!=born:
            raise ValueError('Particle identity reused across births')
        self._births[identity]=born

    def record(self,identity,birth_time,death_time):
        if not all(math.isfinite(float(t)) for t in (birth_time,death_time)) or death_time<birth_time:
            raise ValueError('Finite death time at or after birth required')
        born=float(birth_time);death=float(death_time)
        self.register(identity,born)
        if identity not in self._times or death<self._times[identity]:
            self._times[identity]=death;self._events.append((identity,death))

    def time(self,identity):
        return self._times.get(identity)

    def alive(self,identity,clock):
        if not math.isfinite(float(clock)):raise ValueError('Finite simulation clock required')
        death=self.time(identity)
        return death is None or clock<death

    def events(self,cursor):
        if type(cursor) is not int or not 0<=cursor<=len(self._events):
            raise ValueError('Invalid death-history cursor')
        return len(self._events),tuple(self._events[cursor:])
