# Particle trace collision development

`snow_1024` remains unsupported. It requests standard mode 0, particle killing,
radius scale 1, DEBRIS filtering, and trace accuracy tolerance 256. It also has
random forces and downward initial velocity/gravity; checking only the final
position cannot establish whether its path crossed a surface earlier.

The corrected installed factory is `0x10410494`. Constraint dispatch
`0x101f9740` selects `0x101f8a20` for mode 0 with killing enabled. This branch
uses collision helpers `0x101f6cb0` and `0x101f78a0`; optional confirmation
calls particle-query slot 11. SFM's query implementation is `0x102d3490` in
`ifm.dll`. It delegates to its engine query when configured and enabled;
otherwise it constructs a no-hit trace result. Static inspection alone does
not establish the user's runtime setting or collision geometry filters.

`particle_collision_settings.py` validates the intended standard kill path,
including finite radii, offsets, and trace tolerances. It does not enable the
renderer or change unsupported-effect reporting. The 354-test suite passes.

Remaining implementation requires scene collision geometry with appropriate
Source contents/group filtering, radius-aware traces over the particle's motion
history, persistent death after the first collision, and native Blender tests
that exercise actual intersections. Render-mesh ray tests alone cannot prove
equivalence to Source's BSP and model collision data.

Development now includes `bsp_collision.py` for brush plane/contents extraction
and `particle_brush_trace.py` for convex brush clipping with an axis-aligned
radius hull. Tests cover thin surfaces crossed between samples, expanded-hull
hits, parallel misses, starting inside a brush, nearest-hit selection, and
contents masks. All 361 unit tests pass. Nine vertical traces on the installed
`arena_badlands.bsp` hit brush geometry, and radius-two hulls hit no later than
point traces (`particle_real_map_brush_trace_validation.json`). This does not
prove Source engine trace parity. World-leaf/submodel selection, displacements,
model collision, and persistent particle death integration remain unfinished.

`particle_collision_history.py` now tracks the first impact persistently on
fixed 120 Hz subdivisions. Tests prove that particles remain dead even when
their later trajectory leaves the surface, earlier frame queries retain
pre-impact visibility, and query order does not alter the subdivision path.
The full 364-test suite passes. This is not yet integrated into sprite baking.

The subsequent real-map history test failed its prerequisite: a trace starting
at z=4096 reported start-solid. Inspection of the nine earlier rays showed all
were start-solid. Those results validate finite outputs only, not meaningful
world-surface contact. The reader currently includes submodel brushes in local
coordinates. Before real-map particle validation, select world brushes through
the world model's head node, BSP nodes/leaves, and leaf-brush references; handle
transformed brush entities separately. Do not treat the earlier nine-ray check
as evidence that scene collision behavior works.

Follow-up: `read_world_brushes` now selects brushes through world model zero's
head node, node children, leaves, and leaf-brush indices. A synthetic fixture
proves unreferenced local submodel brushes are excluded. The suite passes 365
tests. The initial real-map trace still started solid after this correction;
therefore the earlier attribution to submodels was not established. Lowering
the trace start from z=4096 to z=512 produced a non-solid start and a surface hit.
Persistent radius-one particle contact then occurred at age 0.109375, matching
the expected planar contact age, and both later and earlier visibility queries
passed (`particle_real_map_collision_history_validation.json`). This validates
the brush/history prototype on that map, not the full Source collision system
or native snow baking.

Development `bake(..., collision_trace=provider)` now integrates persistent
death histories with sprite creation. Without an explicit provider the effect
remains unsupported in normal conversion. The authored snow definition passed
a native probe against a diagnostic horizontal plane 64 Source units below
its initial CP, including particle deaths and 13 saved/reopened frame meshes.
`particle_snow_collision_probe_native_validation.json` records the probe.
The diagnostic plane is not the session's scene geometry; this does not change
the supported-effect count. Production map/model filtering and native tests
with the actual session collision geometry remain required.

The actual `particle test.dmx` snow probe resolved `maps/stage_big.bsp` through
the asset resolver, selected seven world brushes, and killed 2,679 particles
among 4,989 tracked histories. Thirteen native frame meshes saved/reopened.
The probe remains world-brush-only; normal conversion still rejects trace
collision without an explicit development provider. Its frame-60 diagnostic
render is very dim and does not establish SFM appearance parity.

Prepared static brush planes avoid repeated plane validation during sweeps.
All 366 tests pass, including 200 seeded segments compared to the reference
implementation. A 2,000-query `stage_big.bsp` microbenchmark produced identical
results with about 7.1x faster trace calls. Full bake speedup has not been
measured. Evidence: `particle_snow_map_collision_probe_native_validation.json`
and `particle_prepared_brush_trace_benchmark.json` in the output directory.

Evidence in the output directory: `particle_operator_factory_correction.json`,
`particle_collision_dispatch_disassembly.json`,
`particle_collision_trace_helpers.json`, and
`sfm_particle_collision_query_disassembly.json`. Binary inspection was static;
no SFM DLL code was loaded or executed. Release 0.27.84 contains the trace
helpers, but does not enable trace collision in normal conversions.

Further working-tree checks reject dynamic map model entities as well as static
props, brush submodels, displacements and session models before offering the
world-only development provider. Shared collision fades, seeded timing and
control-point strength gates are rejected rather than silently discarded.
All 370 unit tests pass. These additional checks are not packaged yet.

Complete static inspection of helper 0x101f6a30 and the branches beyond the
first return in 0x101f6cb0 found the query mask 0x0200400B, pushed at
0x101f6a98. The world provider now uses that mask rather than solid bit 1.
All 371 tests pass, including individual included bits and an excluded bit.
Evidence: particle_collision_trace_complete_disassembly.json.
Cached-plane tracing, boundary epsilon and full scene coverage remain
outstanding. This mask evidence does not establish Source response parity.

The corrected-mask native probe completed with 13 saved/reopened frame meshes,
4,989 histories and 2,679 collision deaths. An isolated frame-60 render using
the imported session camera contains 135 pixels above RGB 0.01 at 320x180.
It remains dim and is not a Source appearance comparison. Its additive shader
produces color with zero coverage alpha; the pixel check only verifies color.
Evidence: particle_snow_original_camera_probe_render_validation.json.

The new prepare(session, shot, assets) helper resolves the map through the
configured asset mounts, rejects path traversal and unsupported session model
collision, and supplies the guarded provider. The normal worker now requests it
only for enabled trace constraints and records eligibility/failure per shot.
Eligible scenes use approximate kill-on-world-brush collision; unsupported
geometry remains explicitly unsupported. All 374 tests pass. Normal-worker
61-frame integration validation is running; these changes remain unshipped.
