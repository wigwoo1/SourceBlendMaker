# Particle tint integration status

The internal sprite baker accepts `tint_provider(definition, parameters,
shot_time, simulation_time)`. It must return four integer lighting bytes in
0..255. The supplied definition retains its graph instance and parent IDs.
The callback executes while Blender is evaluating the particle birth time.

The sampler applies the authored tint fraction, five decoded blend modes,
byte clamps, amplification, and conversion into Blender linear color.
`SceneTintProvider` binds supplied control-position and packed-light callbacks,
converts positions into Source units, and owns collection caches and immutable
parent history. Its cache keys use graph identity and authored parameters rather
than transient Python dictionary identity. The arithmetic helper owns no cache.
The initial context position remains an explicit caller input. Multiple renderer
passes sharing tint state are rejected until their lifecycle is validated.

Normal conversion still rejects nonzero Color Random tint by default. The source
GUI now offers an opt-in Experimental particle map-light tint switch, and the
worker prepares static BSP lighting when that option is selected. The planner requires explicit
`allow_tint=True`; the baker supplies that permission only when a provider is
present. Maintained-particle tint lifecycle is explicitly unverified and rejected.

Native water and sandwich graph tests passed through this interface without
planner/sampler overrides, saved/reopened 160 meshes, and exactly matched prior
isolated prototype vertices, polygons, UVs, and colors. Those tests supplied a
research map-light/history provider and diagnostic moving control point.
Source invocation cadence, parent-call endpoints, RNG, and exact visual parity
remain unverified. Birth-time sampling is not proof of Source step-time parity.

The optional worker and GUI integration shipped in release 0.28.3.

The production scene binder has also baked and reopened the original two-part
water graph (58 meshes) with a diagnostic moving control, 355 parent reads and
four supplied map-light queries. No planner or sampler overrides were used.
`MapTintQuery` now supplies static BSP ambient/world lighting through the
scoped `particle_tint_lighting` package. Native water validation exactly
preserved all 58 meshes' vertices, polygons, UVs, and colors compared with the
research implementation. Its HDR/ambient policy and lighting settings are
explicit inputs. Dynamic lightstyles, unsupported light types, and unresolved
trace cases fail explicitly. Prop/displacement occlusion and Source engine
cache cadence remain absent. For the worker and GUI integration,
the bounded diagnostic worker job and real Tk folder-queue test both passed.
The saved file reopened natively with 57 finite mesh objects and both 29-frame
timelines. Its tint provider made two lighting queries and 353 parent cache
reads. The GUI forwarded the opt-in setting and displayed live console output.
All 475 source regression tests passed. These checks use a diagnostic copy of
the particle test session with an installed water effect; they do not establish
full original-session or frozen executable validation, or SFM visual parity.
