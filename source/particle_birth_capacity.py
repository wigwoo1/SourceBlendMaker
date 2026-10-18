"""Bound active particle births without rescanning the whole live set."""
import heapq
import math


class ActiveBirthCapacity:
    """Track the live particle capacity for time-ordered birth events.

    Particle emitters and the maintained-count scheduler yield births in
    nondecreasing simulation-time order. Expiry timestamps therefore let the
    bake enforce the same active-count limit in O(log live_particles) per
    birth instead of filtering the complete active list on every birth.
    """

    def __init__(self, maximum):
        if isinstance(maximum, bool) or not isinstance(maximum, int) or maximum < 0:
            raise ValueError('Particle capacity must be a nonnegative integer')
        self.maximum = maximum
        self._expiries = []
        self._last_time = None

    def has_capacity(self, simulation_time):
        simulation_time = float(simulation_time)
        if not math.isfinite(simulation_time):
            raise ValueError('Particle birth time must be finite')
        if self._last_time is not None and simulation_time < self._last_time:
            raise ValueError('Particle births must be ordered by simulation time')
        self._last_time = simulation_time
        while self._expiries and self._expiries[0][0] <= simulation_time:
            expiry,birth_time,lifetime,identity=heapq.heappop(self._expiries)
            # Match the original direct subtraction check exactly. Adding a
            # birth time and lifetime can round to a timestamp whose
            # subtraction still compares as alive (for example .7-.5 < .2).
            if simulation_time-birth_time < lifetime:
                heapq.heappush(self._expiries,
                    (math.nextafter(simulation_time,math.inf),birth_time,lifetime,identity))
        return len(self._expiries) < self.maximum

    def add(self, simulation_time, lifetime, identity):
        simulation_time = float(simulation_time)
        lifetime = float(lifetime)
        if not math.isfinite(simulation_time) or not math.isfinite(lifetime) or lifetime <= 0:
            raise ValueError('Particle birth expiry must be finite and positive')
        heapq.heappush(self._expiries,
            (simulation_time + lifetime,simulation_time,lifetime,int(identity)))


class DeathAwareBirthCapacity(ActiveBirthCapacity):
    """Death-aware capacity for culling; ordinary birth tracking is unchanged.

    Death events can be recorded after a birth was admitted. Heap entries are
    invalidated by identity/token, so an early death cannot free a slot twice.
    Authored lifetime still controls the natural-expiry subtraction boundary.
    """
    def __init__(self,maximum,deaths):
        super().__init__(maximum)
        self.deaths=deaths;self._cursor=0;self._active={};self._token=0;self._seen=set()

    def has_capacity(self,simulation_time):
        now=float(simulation_time)
        if not math.isfinite(now):raise ValueError('Particle birth time must be finite')
        if self._last_time is not None and now<self._last_time:
            raise ValueError('Particle births must be ordered by simulation time')
        self._last_time=now
        self._cursor,events=self.deaths.events(self._cursor)
        for identity,death in events:
            if identity in self._active:
                born,life,token=self._active[identity]
                heapq.heappush(self._expiries,(death,identity,token))
        while self._expiries and self._expiries[0][0]<=now:
            _,identity,token=heapq.heappop(self._expiries)
            entry=self._active.get(identity)
            if entry is None or entry[2]!=token:continue
            born,life,_=entry
            if now-born<life and self.deaths.alive(identity,now):
                heapq.heappush(self._expiries,(math.nextafter(now,math.inf),identity,token))
            else:del self._active[identity]
        return len(self._active)<self.maximum

    def add(self,simulation_time,lifetime,identity):
        born=float(simulation_time);life=float(lifetime)
        if not math.isfinite(born) or not math.isfinite(life) or life<=0:
            raise ValueError('Particle birth expiry must be finite and positive')
        if type(identity) is not int or identity<0 or identity in self._seen:
            raise ValueError('Unique nonnegative active particle identity required')
        self.deaths.register(identity,born);self._seen.add(identity)
        self._token+=1;token=self._token
        self._active[identity]=(born,life,token)
        death=self.deaths.time(identity)
        expiry=born+life if death is None else min(born+life,death)
        heapq.heappush(self._expiries,(expiry,identity,token))
