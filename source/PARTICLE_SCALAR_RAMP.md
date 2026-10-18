Scalar ramps (development source)
================================

Ramp Scalar Linear Random currently supports radius field 3 and roll field 4. Rates and time
windows are sampled once per birth, then applied at the authored position in
the radius operator sequence. Later radius scales or remaps may overwrite it.
Descending authored ranges are preserved. Disabled ramps do not consume draws.

Static installed-engine inspection established additive rate increments,
lifetime-positive gating, exclusive end times, field clamps, and a default
whole-life proportional-window optimization. The converter uses its approximate
120 Hz history and random stream; Source tick and random alignment are unverified.
Roll rates are applied directly at the radian scalar boundary, based on installed
float metadata and operating code. Roll requires animated-sprite geometry and
uses ordered history with basic rotation, spin, and scalar oscillation. Four
history unit tests and a native synthetic Blender sprite-state check passed;
original roll-effect graph bake/render validation is still pending.
Timed/external strength and other ramp fields are rejected pending integration.

The original water_upjet_g PCF passed a diagnostic bake of 12 frames over two
seconds, finite geometry, packed save/reopen, and a 96x96 sampled render with a
measurable particle-hidden contrast. It used stationary diagnostic control
points and actual stage_big map tint. This does not prove full-session or SFM
visual parity. The 0.28.12 downloadable ZIP predates this feature.
