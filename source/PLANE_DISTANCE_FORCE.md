# Plane-distance force development

The pure math module particle_plane_force implements the installed force's
signed world-space distance, clamped interpolation between two authored vectors,
and nonnegative quarter-step exponent. The authored normal is neither normalized
nor rotated. Equal distance endpoints select the minimum force for positive
exponents. Exponent zero yields the maximum force, matching power-zero behavior.
Negative exponents remain rejected because Source's zero-safe reciprocal and SSE
approximation need additional verification.

Static evidence is in particle_plane_distance_force_disassembly.json and
particle_plane_force_power.json. The installed DLL was only read as bytes, never
loaded or executed. Development now wires a single plane force into the baker
using 120 Hz midpoint integration, world/Source unit conversion, and CP animation
sampled through the inverse particle simulation clock. Combined forces, movement
lock, and nondefault shared timing/strength remain rejected. Five targeted tests
cover the formula, analytic constant-force motion, and CP clock sampling; the
325-test suite passes. The isolated native I dunno_copy test saved/reopened 63
particle mesh frames and 31,541 nondegenerate quads, with finite vertices, material
slots, and particle color attributes. It preserved the original plane force and
both lifetime modules but removed Color Fade and set the curve's shared random
scales to one. These overrides prevent claiming the complete authored effect
works. A final render and live Source parity remain unverified.
The latest distributed application remains 0.27.80.
