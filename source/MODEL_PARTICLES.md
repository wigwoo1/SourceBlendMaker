# Model-attached particle implementation status

Introduced in 0.28.4. The scoped native path below has passed baking,
save/reopen and diagnostic rendering. Full-session and Source visual fidelity
remain unverified.

The authored `pokemon.dmx` system `magic_aura_large2` references the child Hobkin
game model. Its embedded graph contains Position on Model Random and Movement
Lerp to Hitbox. Both use control point 0 and the default hitbox set; authored
placement uses scale 1, no direction bias, no inside-model retries and desired
hitbox -1. Lifetime lerp start/end are 0 and 1.

`model_hitboxes.read` reads the classic MDL44-49 hitbox layout with bounds,
bone-index and finite-value validation. `model_hitbox_binding.Binding` evaluates
bone-local boxes and persistent normalized coordinates in Blender world space.
Native checks resolve all 78 child Hobkin boxes and compare eight corners and
the center at frames 1, 13 and 25. These checks establish imported geometry and
animation binding, not Source placement distribution or visual equivalence.

The initial factory association was invalidated by metadata validation: the
tables following each name belong to neighboring operators. Correct factory
tables are 0x1041304c (model random) and 0x10418a04 (hitbox lerp), with instance
tables 0x10413b6c and 0x1041b89c respectively. The earlier movement entry at 0x10279880
belongs to Movement Lock to Bone, not Movement Lerp to Hitbox. Its prototype
arithmetic must not be used to implement hitbox lerp. That neighboring entry
uses current and previous hitbox records and normalized coordinates, transforms
both, subtracts them, and adds a weighted delta to particle positions. This is
an inference from arithmetic and memory accesses, not runtime verification.
The corrected hitbox lerp entry is 0x10279590. It skips age <= start and
age >= end, and independently blends both particle position fields toward the
current hitbox point using (age-start)/(end-start) times supplied strength.
`particle_hitbox_lerp` reconstructs this observed ordinary positive-end range
with float32 operations. The scene adapter now supplies this motion to native
sprite geometry; arithmetic alone does not establish runtime parity.
All 493 source tests pass.
Special nonpositive-end substitution, exact lifetime/time weighting,
collection hitbox update cadence, initializer random selection and query
dispatch still require verification before enabling this path.

Evidence: outputs/particle_hitbox_factory_disassembly.json,
outputs/particle_hitbox_instance_disassembly.json,
outputs/hobkin_authored_particle_graph.json and
outputs/hobkin_animated_hitbox_validation.json in the development workspace.
Only binary bytes were inspected; no installed DLL code was executed.

The recursive authored graph audit now retains element IDs and resolves each
operator reference by ID. Both aura definitions have zero-rate position
oscillation before hitbox lerp, so that oscillator contributes no movement.
Model selection, chronological particle state and immutable history helpers
are implemented and connected through `particle_model_scene` in the worker.
Native history checks use 32 particles and 121 snapshots on a diagnostic
120 Hz clock; this does not establish Source tick phase or full graph parity.

The integration handles default unbiased scale-one model placement, optionally
followed by one ordinary positive-end hitbox lerp on the same model and set.
Without hitbox follow, ordinary Movement Basic gravity/drag is retained after
model placement, so emitted sprites can move away from their birth position.
Additional position writers, spatial forces and constraints require ordered
integration and currently produce an explicit unsupported reason. Original
definitions are retained; an internal planning copy substitutes the placement
stream while the adapter supplies world positions to the baked sprite vertices.
Shared model poses use Blender frame/subframe cache keys and immutable copied
bone matrices. Particle histories remain separate, so repeated/backward render
queries do not apply the follow movement twice.

Native integration evidence uses the original `pokemon.dmx` aura and child
sparkles at authored frames 15186-15216, preserving the original shot origin
and emission clock. Both effects generated 30 frame meshes (60 total), 550
births, 8,501 nondegenerate sprite quads and 17,272 history snapshots. The file
saved and reopened successfully. A Cycles CPU diagnostic-camera render at
frame 15216 changed 4,955 pixels when the particle collections were excluded;
this establishes visible contribution in that diagnostic view, not SFM fidelity.
Twelve cached-pose checks across three fractional frames and four hitboxes
matched live Blender coordinates exactly. Both bindings also passed with a
cold MDL cache. Other models and the map were omitted from this bounded fixture.
Receipts: outputs/hobkin_model_particle_bake_validation.json,
outputs/hobkin_model_particle_render_validation.json and
outputs/hobkin_model_factory_validation.json.

Two unchanged installed definitions, pumpkin_sparkle and halloween_pickup_active,
also passed model-spawn movement baking using the benchmark's model and control
timing. Their final sprite centers matched independently computed gravity/drag
displacement within 0.5 mm (including the renderer's depth epsilon); maximum
upward movement was 0.43 and 0.53 m. This fixture substitutes those installed
definitions into the diagnostic controls; it is not their authored appearance
in pokemon.dmx. Both saved and reopened with finite geometry. All 494 source
tests pass. A topology-only audit finds 11 conditionally eligible variants among
186 installed model-placement/follow variants; actual scene bindings, assets
and native/SFM rendering are additional gates.

Unreleased work after 0.28.4 adds finite nonnegative model hitbox scales.
The installed SFM query uses endpoint mapping [1-scale, scale], with separately
rounded float32 subtraction, multiplication and addition. This differs from
ordinary scaling around the box center. Scale 0.5 selects the center; scale
0.75 maps random coordinates into [0.25,0.75]; values above one can extrapolate
outside the box. Selection, persistent state, animated binding and shared pose
cache preserve those coordinates. All 495 source tests passed at that stage, and nine native checks across
three fractional animation frames match independent transformed coordinates.
Two diagnostic effect graphs with scales 0.75 and 2 passed native baking,
movement checks and save/reopen. Those diagnostics edit the scale of installed
sparkle definitions; they are not original SFM visual comparisons. The 20
variants formerly blocked first by scaling still encounter other unsupported
features, so the conditional topology count remains 11/186.
Evidence: outputs/sfm_model_selection_constant_audit.json,
outputs/model_scale_native_validation.json and outputs/model_scale_bake_validation.json.

Further unreleased work follows the installed SFM model-query behavior for
direction bias and surface tracing. Static inspection shows that its query
does not read the supplied direction vector; requesting surface tracing emits
a warning but does not alter hitbox selection. The converter now preserves
that behavior and records ignored settings in the conversion report, rather
than rejecting these settings or inventing a displacement. This policy is
specific to SFM and does not assert behavior of other Source games.
All 497 source tests pass. Two diagnostic graphs with nonzero bias and surface
flags passed baking and save/reopen. Their 57 saved meshes match the unbiased
baseline exactly for vertices, polygons, UVs and colors. No SFM runtime visual
comparison was performed. The topology count remains 11 eligible / 175 rejected
among 186 model variants because downstream unsupported operators remain.
Evidence: outputs/model_query_bias_argument_trace.json,
outputs/model_query_policy_bake_validation.json and
outputs/model_query_policy_geometry_validation.json.

Further unreleased integration handles one same-model Movement Lock to Bone
operator with ordinary Movement Basic in authored order. Default zero fade end
uses SFM's effectively unbounded sentinel. Rigid locking writes both position
buffers; ordinary following adds model movement while preserving velocity.
Animated control-point translation supplies the jump threshold check. Startup
bypass timing, exact Source ticks and visual parity remain unverified and are
reported in conversion diagnostics. Immutable snapshots permit repeat/backward
queries without applying motion twice.
All 511 source tests pass. Two diagnostic sparkle graphs edited to add ordinary
and rigid bone locking passed native baking, finite geometry and save/reopen;
this is not an untouched authored SFM effect comparison. The topology-only
model audit now finds 24 conditionally eligible and 162 rejected variants out
of 186. Actual bindings, assets and rendering are additional gates; the broad
audit remains 3,640 rejected variants and was not reduced by this local audit.
Receipts: outputs/model_bone_lock_bake_validation.json,
outputs/model_motion_native_validation.json and
outputs/installed_model_particle_topology_audit.json.

Two unchanged installed definitions, community_sparkle and ghost_glow, also
passed the production model factory and sprite baker on the animated benchmark
binding over frames 15186-15276. These definitions were substituted into the
benchmark controls; they are not the authored effects in pokemon.dmx. Both
generated finite geometry and saved/reopened successfully (119 frame meshes).
At the final sampled frame their 1 and 22 sprite centers matched the adapter's
simulated positions within 0.3 mm. Histories recorded 62 and 2,553 snapshots;
this checks conversion plumbing, not an independent SFM simulation reference.
A diagnostic Cycles CPU render at frame 15265 changed 4,420 pixels when these
particle collections were excluded. Both images were inspected: the effects
add a visible glow around the model. This establishes contribution in that
view, not Source camera, shading or motion parity.
Receipts: outputs/installed_bone_lock_bake_validation.json and
outputs/installed_bone_lock_render_validation.json.

Velocity Random and Velocity Noise now feed sampled world velocity into
bone-following history. Installed SFM dispatch places both in its second pass,
after model placement regardless of authored list order. Both scalar routines
modify previous position without reading the incoming write mask. The adapter
therefore also admits these velocity initializers before placement in the list.
All 512 tests pass. Two edited
diagnostic graphs with 100 Source units/second random velocity passed native
initial-buffer speed checks, sprite geometry checks and save/reopen. This is
component/conversion evidence rather than an original SFM effect comparison.
The model topology audit now reports 29 conditionally eligible / 157 rejected
out of 186. The broad audit count remains unchanged.
Receipt: outputs/model_velocity_bake_validation.json.

The diagnostic graphs also passed with Velocity Random moved before model
placement in the authored initializer list. Both saved/reopened successfully;
all saved particle mesh vertices, polygons, UVs and colors matched the
post-placement-list baseline exactly. This verifies converter ordering and
saved geometry against its own baseline, not SFM runtime visual parity.
Receipts: outputs/model_velocity_early_bake_validation.json and
outputs/model_velocity_order_geometry_validation.json.

Movement Basic combined with same-model Movement Lerp to Hitbox now also uses
ordered motion history. Both current and previous buffers interpolate after
movement when authored in that order. The reversed order preserves the later
gravity update. All 514 tests pass. Two diagnostic graphs edited to add this
combination passed native finite geometry checks and save/reopen; their final
sprite centers matched adapter history within 0.5 mm. This is not an original
SFM effect or independent Source simulation comparison.
Receipt: outputs/model_ordered_lerp_bake_validation.json.
