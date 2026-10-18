Development world-axis force arithmetic follows installed force 0x101fb170.
Metadata defaults are amount 0, axis (0,0,1), local-axis false and control point 0.
The axis is normalized. Particle displacement from the selected control point
is normalized, then the installed instruction sequence subtracts radial * dot
from radial, normalizes again and crosses that vector with the axis. Force
magnitude is amount times shared strength. Distance and reduced-vector squared
lengths must exceed the installed constant 2^-23.

The subtract sequence is preserved as observed rather than replaced by the
conventional projection formula. Python normalization differs from Source SSE
reciprocal-square-root rounding. Three arithmetic and two spatial integration
tests pass. Development connects world-axis twisting to the experimental pull
simulator, sampling the twist control point at each integration step. Original
kamehameha1_outerexplosion2 modules and parameters were retained in an isolated
native test: 62 sampled particle meshes saved and reopened, and a fitted-camera
Cycles sample at frame 60 visibly renders the effect. Local axes, Source tick
ordering and trajectory comparison remain unverified. Released version 0.27.83
is historical. Release 0.28.1 includes ordered world-axis twist with position
vector oscillation, including animated imported control points. Version 0.28.2
also connects twist to ordered movement without requiring vector oscillation,
and to ordered experimental pull movement. Local axes and exact Source
appearance and trajectories remain unverified.
