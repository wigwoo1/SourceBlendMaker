# Particle planes, point-light colors, and omitted defaults

The converter supports `Prevent passing through a plane` for sprite particles.
It transforms authored plane origin/normal using the selected control point,
honors global origin/normal flags, and projects the particle center to provide
clearance for its animated radius. Projection occurs at sampled frames;
Source's iterative collisions and force history between frames remain unverified.
Plane constraints on trail/rope renderers and strength fades are rejected.

`Color Light from Control Point` supports four static point-light descriptors,
world-space offsets, initial-color bias and minimum/maximum initial-color
clamps. Dynamic lights, spotlights, computed normals, strength fades and combined
color fades remain rejected. Installed SFM Operate copies light 3's descriptor
for light 4 while retaining position 4; this observed installed behavior is
preserved and recorded in conversion reports. Exact SIMD rounding and tick
ordering remain approximate.

The installed unpack tables establish continuous emission_rate=100 and
Lifetime Random endpoints=0, exponent=1 when omitted. A zero minimum with a
positive maximum is valid. Both lifetime endpoints zero remain rejected as
an effect without a positive supported lifetime.

Arithmetic references: Valve's public LightDesc SetupNewStyleAttenuation and
ComputeNonincidenceLightAtPoints, and mathlib SolveInverseQuadraticMonotonic:
https://github.com/ValveSoftware/source-sdk-2013/blob/master/src/mathlib/lightdesc.cpp
https://github.com/ValveSoftware/source-sdk-2013/blob/master/src/mathlib/mathlib_base.cpp
Installed pet.dll static evidence SHA256:
340b0278d7258015a1bd9fd6cc4068d593469dee999eec15667f85a776f5e506
No installed DLL code is loaded or executed for this analysis.

The authored I dunno_copy2 definition from particle test.dmx is tested with
all its original modules and no parameter substitutions. Native save/reopen
and a diagnostic render do not establish complete live SFM visual parity.
