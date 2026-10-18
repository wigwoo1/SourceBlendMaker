# Model-position particle investigation

The saved `particle test.dmx` contains `magic_aura_large_sparkles1`, with one
control-point transform and an empty `controlModels` array. Its PCF uses
`Position on Model Random` with default parameters. This effect remains unsupported.

Static inspection of the installed SFM `pet.dll` confirms the initializer at
`0x1022b7f0` calls a particle-query interface (manager member `0x13c`, virtual
slot 16) at `0x1022b929` to supply positions, hitbox coordinates, and hitbox
indices. It does not implement the no-model fallback inside the initializer.

The preceding helper at `0x101eca90` refreshes control-point data through the
same query interface, virtual slot 19. It allocates two 0x4800-byte buffers,
swaps the buffers when simulation time changes, and requests up to 256 entries.
These buffer sizes and dispatches alone do not prove their complete data layout.

The SFM implementation has now been identified by its RTTI type
`CDmeParticleSystemQuery` in `ifm.dll`, vtable `0x10aebb8c`. Slot 16 is
`0x102d3bc0`. Its branch at `0x102d3f14` handles missing control models or
unavailable hitboxes by copying the control-point position into each output
position and zeroing hitbox coordinates/indices. The default query in `pet.dll`
instead writes zero positions; it is not the SFM fallback.

Development code now resolves the unattached-model position initializer to
control-point emission. It preserves the source definition and rejects attached
models and unverified shared timing gates. The 348-test unit suite passes.
Initial native testing exposed `Oscillate Vector` and `Movement Lerp to Hitbox`.
Subsequent static inspection established the authored zero-rate position
oscillation contributes nothing. The hitbox movement operator at `0x10279590`
tests the refreshed hitbox count at `0x102795d6` and exits at `0x10279873` when
it is zero. SFM's query slot 19 returns zero with no attached model.

Development now handles both cases. The 351-test unit suite passes, and the
authored sparkle effect generated 13 native frame meshes (1,733 sprite quads)
across 14 sampled frames, saved/reopened successfully, and produced a visible
frame-60 render with its original material. This is sampled native validation,
not full-session or Source visual parity. Nonzero vector oscillation and
attached-model hitbox movement remain unsupported. These changes are unshipped.

Factory association was corrected during follow-up inspection: the registration
object's vtable precedes its name pointer. The neighboring entries are Vector
Oscillation Simple and Movement Lock to Bone. Correct factories are `0x10418374`
and `0x10418a04`, recorded in `particle_operator_factory_correction.json`.
Vector Oscillation uses separate rate/frequency minimum and maximum vectors;
Hitbox Lerp uses `control point number`. Development validation uses these keys.

For attached models, conversion also needs
the selected MDL hitbox set and animated bone transforms. Sampling the visible
mesh surface would not establish equivalent behavior.

Evidence: `particle_model_attachment_audit.json`,
`particle_curve_position_disassembly.json`, and
`particle_model_query_disassembly.json`, `sfm_particle_query_disassembly.json`,
and `particle_model_fallback_native_failure.json` in the output directory. The installed
binary was read as bytes only; its code was never loaded or executed. This note
describes development investigation and does not add support to release 0.27.83.
