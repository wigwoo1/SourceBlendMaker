# Experimental particle attachment fades

The optional GUI setting enables age-based translation attachment fades for
sprite particles, including `magic_fire_smoke` in `particle test.dmx`.
It is disabled by default and is preserved for queued conversions.

The installed SFM parameter mapping, clamped linear fade, quarter-step positive
random exponents, and jump-threshold branch were inspected statically.
Source code was never executed from the installed DLL.

The converter integrates control movement over an approximate 120 Hz
simulation-age history. Source random streams, tick phase, operator ordering,
and complete visual matching remain unverified. Rotation locks with age fades,
distance fades, overlapping fade ranges, and faded trails/ropes remain unsupported.

The original fireball smoke and a moving-control fixture saved and reopened as
13 sampled native meshes each; isolated frame 10 renders produced visible pixels.
The mounted `effects/wispy_smoke2.vtf` has nearly opaque alpha (0.961–1.0), also
confirmed with an independent DXT5 alpha check. The diagnostic smoke looks like
a red card; this is not evidence of SFM visual parity. No original asset is changed.
