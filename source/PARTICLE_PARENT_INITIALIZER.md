# Parent-particle initializer foundation

`particle_parent_sample.py` implements verified arithmetic from the installed
Source particle initializer. Source GUI conversions can opt into
**Experimental parent-particle spawning**; the setting also follows batch jobs.
It remains disabled by default. The published 0.28.10 ZIP does not include this
development option yet.

Verified rules:

- Sequential indices above the final active parent reset to zero, rather than
  wrapping with modulo.
- Random selection with integer increments chooses a discrete parent; a
  fractional increment chooses a continuous index across the first-to-last
  parent range.
- Creation-time interpolation uses float32 tick boundaries. A zero or
  rounded-away timestep uses a time boundary comparison.
- Inherited motion is measured from the parent's previous position to the
  interpolated birth position, rather than across the entire tick.

Development integration retains parent current/previous buffers, stable instance
identities, rendererless simulation and child birth scheduling when an explicit
simulation context map is supplied. The GUI option supplies that map per system.
Source death handling, RNG alignment and exact tick timing remain
unverified. Negative selection cursors/increments remain rejected. The helper
does not guess positions from rendered meshes or synthesize missing parents.

The collection-view prototype now retains births, lifetimes, origins and a
bound sampler, and queries approximate current/previous positions in Source
units. It uses birth ordering and lifetime boundaries; it does not reproduce
Source death compaction or killed-parent dispatch. Full rigid locks and
experimental translation-fade locks feed the retained simulation sampler;
collision and other unsupported constraints still prevent exporting a context.
Shared initializer strength/time settings outside their default values are
rejected rather than silently ignored. Delayed lifetime gates still prevent
exporting parent histories; a default zero-time decay gate does not extend the
lifetime and can use ordinary parent buffers. Combined parent/model-hitbox
spawning and killed-parent-only dispatch are unsupported.

Validation includes 17 original installed PCF graphs at five diagnostic sample
times: each generated finite parent/child geometry, saved and reopened, and
produced visible pixels in a diagnostic render. Five additive effects were also
rendered against an opaque background to verify RGB emission despite zero alpha
on transparent film. Reversing definition order still generated all 17 graphs.
These are stationary-control fixtures, not visual comparisons with SFM or
full-duration validation of those effects. The original user-session full
conversion is being validated separately.

Static evidence is recorded in the workspace's parent-particle metadata and
scalar boundary receipts. No installed binary code was executed for inspection.


## Pull and lock combinations in Pokemon sessions

The default bake path rejects combined pull forces and Movement Lock to Control Point. The optional development path has passed both original combine-explosion PCF diagnostic benchmarks described below. Saved Pokemon descriptors place Movement Basic before the translation lock; homing variants also place position oscillation after the lock. A correct implementation needs chronological motion history so subsequent force evaluations see the locked position. Applying a final displacement to an independently integrated pull trajectory does not establish equivalent motion. Parameters and order are recorded in pokemon_pull_lock_order_audit.json; native SFM timing remains unverified.


The development bake API now has a `development_pull_lock` flag (default false;
exposed by the unreleased GUI option Experimental particle forces with translation locks). It integrates movement, full translation attachment,
and position oscillation in authored order. Rotation locks, randomized
attachment fades, distance fades, and shared lock timing/strength remain
unsupported. A bounded per-birth tick cache preserves the reference query
results, including rewind and exact-tick boundaries. Unit tests verify unit
scaling and cache equivalence. Original-PCF native bake and animated-control
save/reopen/render validation passed the diagnostic cases reported below;
full authored-session validation remains pending. This path is not yet a released
compatibility claim and does not establish Source visual parity.


The latest development validation baked both original Pokemon combine-explosion
PCF graphs with animated diagnostic control-point motion, with no failed branch
records and finite parent/child meshes. Their packed files saved and reopened;
saved PNG RGB checks found 4166 and 4019 colored pixels. This is sampled graph
validation, not full-session or SFM visual-parity proof. The GUI option is off by
default and travels with single and bulk jobs; the worker forwards it to the
same tested bake API. Release packaging and full DMX validation remain pending.
