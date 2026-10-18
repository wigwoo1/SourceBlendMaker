# Deferred particle mesh linking — validation history

## Current promoted implementation

The per-system animation sampler now skips redundant `scene.frame_set` calls
when a collision or particle-history query requests the same exact integer
frame and subframe again. A 61-frame `particle test.dmx` A/B conversion measured
207.484 seconds without the guard and 147.090 seconds with it (29.1% faster on
this run). Both outputs completed, and native Blender comparison found 1,281
particle meshes in each with identical mesh sets, vertex positions, faces,
colors, UVs, material assignments, and object transforms. Receipts:
`outputs/particle_frameguard_ab_comparison.json` and
`outputs/particle_frameguard_benchmark.json`. This is a single-host timing and
does not establish Source visual parity or full-animation performance.

The full baseline and deferred-link/unlink candidate both completed the normal
particle test.dmx conversion over frames 1–61. Native reopening verified 1,638
finite particle meshes, including 60 snow meshes and world-brush collision deaths.
All 1,638 meshes match exactly between both outputs for vertices, faces, colors,
UVs, transforms and material names. Evidence:
outputs/particle_normal_collision_validation.json,
outputs/particle_normal_unlinked_validation.json and
outputs/particle_mixed_unlinked_geometry_comparison.json.

The isolated-reference mismatch is retained in the diagnostics: the full bake
includes an earlier definition that increments camera-depth ranks, while the
isolated bake omits it. Colors, UVs and faces were equal; position differences
followed the camera normal. The full-to-full comparison resolves this scope
problem. No Source visual parity or complete-animation claim is established.

Production now defers linking newly generated sprites and temporarily unlinks
completed sprite-only root collections while sampling later particle systems.
Controls and mixed collections stay active; links restore in finally. The
Geometry Nodes suspension and float32 time-alias prototypes remain unshipped.
The sections below record earlier experiments and their status at that time.

This unshipped candidate keeps the generated sprite collection unlinked while sampling control-point animation, then links it before restoring the frame and saving. This avoids evaluating newly generated sprite meshes during subsequent scene.frame_set calls.

The isolated I dunno_copy bake completed in 33.805 seconds, saved and reopened 61 frame meshes containing 30,540 quads. Its vertex positions, polygon indices, color attributes and UVs match the original isolated reference exactly at all 61 frames. Evidence: outputs/particle_display_deferred_native_validation.json and outputs/particle_display_native_geometry_comparison.json. The comparison also verifies the candidate module path in the bake log.

This does not establish Source renderer parity or whole-conversion performance. The mixed particle test.dmx conversion is running using work/particle-display-candidate/blender_worker.py and work/particle-normal-display-collision-job.json; its output is work/particle-normal-display-collision-preview.blend. The production source and released archive have not been changed by this candidate. Maintained-sprite special paths and full mixed-project save/reopen still require validation before promotion.

A separate native Blender fixture now verifies that suspension leaves mixed control/sprite collections active, preserves collections that were already hidden, and restores completed sprite visibility after a deliberately raised exception. Evidence: outputs/particle_bake_visibility_native_validation.json. The suspension helper remains unshipped in work/particle-display-candidate/particle_bake_visibility.py. A wrapper candidate is isolated in work/particle-suspended-candidate; the unchanged full mixed candidate worker continues running separately. No current running worker code was modified.

The combined deferred-linking/suspension wrapper completed a 61-frame isolated bake, saved/reopened the native file, and exactly matched reference vertices, polygons, colors and UVs (outputs/particle_suspended_native_geometry_comparison.json). The isolated run does not contain preceding sprite systems, so the separate native visibility fixture is the evidence for active suspension/restoration. A full mixed-session wrapper test is now running with explicit runtime candidate-module path assertion in work/particle-suspended-candidate/blender_worker.py. Earlier mixed workers are still running unchanged; none was restarted because of an observation timeout. Full mixed comparison and collision verifiers are prepared and await completed outputs.

Correction after inspecting the current installed-definition inventory: 11,706 inventory records contain only one maintained-emitter definition rejected by the shared planner, tractor_beam_arm (Normal Align to CP). That initializer is also rejected by the maintained Geometry Nodes fallback. The scan is recorded in outputs/maintained_particle_fallback_candidates.json. Consequently, there is currently no evidence that completed maintained Geometry Nodes geometry causes the mixed particle test slowdown; the GN suspension helper is a passing synthetic fixture but remains unnecessary/unshipped pending a real supported case. Two older native files contained no maintained-node objects and their attempted authored-restoration checks failed the precondition; they do not prove authored restoration. Do not infer production coverage from those attempted tests.

## Full-scene dense-effect profile and time-cache candidate

The unchanged combined candidate, restricted diagnostically to I dunno_copy but retaining the actual imported map/control hierarchy and 61-frame source animation, completed in 82.306 profiler seconds. Particle bake cumulative time was 64.562 seconds; target_at_clock 41.956 seconds; 97,657 set_time calls 20.920 seconds. This is a diagnostic selected-effect conversion, not the completed mixed-session benchmark. Its saved native geometry/colors/UVs match the isolated reference exactly across all 61 frames (outputs/particle_dense_full_scene_geometry_comparison.json).

A native alias fixture evaluated all imported control transforms over 140 frame-time samples including tiny positive/negative jitter. Matrices matched exactly within groups using float32(integer_frame + float32(subframe)); evidence outputs/particle_target_time_alias_native_validation.json. A candidate cache key using that precision is isolated in work/particle-time-alias-candidate. The 61-frame selected-effect profile is running with explicit runtime assertions for both candidate baker and time-cache module paths. Exact native geometry comparison is still required before promotion. Production cache keys remain unchanged. No full mixed worker was restarted or stopped because of elapsed observation time.

The float32-total-frame cache candidate completed and preserved all 61 native mesh/color/UV hashes (outputs/particle_time_alias_geometry_comparison.json). It reduced set_time calls only from 97,657 to 97,620. Total profiled time was longer under concurrent load (137.594 seconds vs 82.483); this does not demonstrate a performance gain, and the cache change will not be promoted. Birth times distributed inside maintained-count ticks produce many genuinely distinct target queries; precision aliasing alone does not explain the bottleneck.

A separate unshipped unlinking helper now temporarily removes completed sprite-only collections from the scene rather than hiding them. Its native fixture proves they disappear from scene.objects and the evaluated graph, while animated controls, mixed collections and prior hidden states are preserved and restoration occurs after an exception (outputs/particle_unlink_suspend_native_validation.json). Runtime performance and complete native output comparison remain pending. The previously running workers remain unchanged.

Three exact own hiding-only workers were deliberately retired after confirming their command lines and successful termination: display-only, collection hide_viewport, and hide_viewport plus GN. Their conversions were incomplete, not successful references. Receipt: outputs/particle_superseded_candidate_terminations.json. The baseline cached normal worker remains running. A new full mixed-session candidate uses deferred linking and scene-root unlink/restoration, retaining the original production time cache and omitting the unnecessary GN modifier helper. It runs from work/particle-unlinked-candidate/blender_worker.py with work/particle-normal-unlinked-job.json. Native collision/nonfinite-data and full mixed geometry/color/UV/material/transform comparators are prepared for its completed output. No source or release has been promoted from these experiments.
