Plane-distance force motion uses a sparse fixed-tick history cache. It keeps
checkpoints every 30 ticks and the latest complete tick; partial query steps
are recomputed and never stored as a new simulation boundary. Queries made
out of order replay from an earlier checkpoint. Target motion and force
settings must remain unchanged during one particle's bake.

The prepared inverse clock validates timing segments once and searches the
relevant clock interval. It preserves the reference's pause, speed-ramp,
minimum-time and boundary-tolerance branches.

Verification includes 1,000 motion comparisons, 4,200 inverse-clock comparisons,
a Blender control-point comparison, and a 61-frame native particle bake whose
vertices, faces, colors and UVs match the original baker exactly. The first
native test accidentally loaded the reference baker due to import precedence;
the corrected candidate test asserts its module path before baking.

These comparisons establish equivalence to the converter's existing
approximate integration, not Source tick or rendering parity. The full-session
normal-worker check remains pending. Small benchmark speed ratios do not
predict total conversion time; scene updates and other operators still cost
time. Release packaging is pending that normal-worker verification.
