# Random ring particle initialization

Zero-thickness `Position Along Ring` now initializes ordinary sprite particles,
including authored radius, QAngle rotation, control-point rotation, radial
speed and the XY-only velocity flag. Override control points and nonzero
thickness remain explicitly rejected. Evenly spaced rings remain restricted
to the experimental spline path.

The installed SFM initializer at 0x102038c0 increments its context counter,
then multiplies a fresh random angular step by that counter. The converter
uses this structure, but its seeded random stream and birth-counter reset
timing remain approximate. This is not a verified live Source simulation match.

Validation: three additional arithmetic tests; 301 total unit tests pass.
An isolated initializer from `particle test.dmx` / `I dunno_copy2` produced
238 native animated mesh frames, saved/reopened successfully, and rendered
visibly with its original glow material.

That isolated test explicitly removed `Color Light from Control Point` and
`Prevent passing through a plane`, and supplied test values lifetime_min=1
and emission_rate=10. It does not prove the complete authored effect works.
Production conversion continues to reject unsupported modules and unverified
omitted defaults instead of silently omitting those parts.
