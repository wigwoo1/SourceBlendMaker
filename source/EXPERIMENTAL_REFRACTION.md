# Experimental particle refraction

Release 0.27.64 includes this experimental path. The GUI exposes
an opt-in Experimental particle refraction checkbox, disabled by default unless
a saved preference enables it. Single and queued jobs preserve the setting.
The development GUI startup self-test passes outside the execution sandbox;
the sandboxed runtime cannot initialize Tcl even with its files present.
Development worker jobs can set `experimental_refraction: true` to route Refract
materials through this path. Default conversion still reports them unsupported.
The worker creates materials separately per shot and tentatively uses shot.start
as texture time offset. That phase mapping needs session validation. Development
source snapshots static maintained geometry nodes into independent frame meshes;
the procedural original is retained in a render-disabled collection. Moving
maintained effects already use frame meshes. This increases file size.
Worker routing has been exercised with diagnostic copies of fireflies.dmx,
replacing one effect with the installed heat_wave definition. Three-frame and
31-frame conversions saved and reopened without conversion errors. These are
modified diagnostic sessions, not proof of all original-session effects.

The experimental material loader connects signed normal-map displacement,
normal alpha, vertex modulation, tint textures decoded from sRGB, and silhouette
fade. Cyclic AnimatedTexture proxies can drive packed normal or tint frames.
Frame 1 plus an explicit time offset defines Source time. The driver follows
scene FPS and FPS base. Extracting session and shot phase remains unverified.
Unsupported proxies and non-wrapping animation remain rejected by scene setup.

Scene setup composites independent primitives in approximate camera depth order
across effects. Different blur settings use separate passes at the same rank;
only one rank/blur combination should be active at a given frame. Callers must
supply matching baked frame samples and mutually exclusive meshes within each
effect. Camera edits require rebuilding the ordering. Existing compositors with
one connected local primary render-layer node are copied, with refraction added
before downstream effects. Multi-layer graphs and transparent film output remain
unsupported.

Native Blender evidence is saved outside this source directory:

- `refraction_animated_render_validation.json`: original 29-frame water normal
  texture; animated render matches static frames 0, 1 and 28, loops, and reopens.
- `refraction_multi_scene_validation.json`: two overlapping diagnostic effects
  with different tints and blur settings; depth rank checked, render reopens.
- `refraction_multi_animation_validation.json`: two effects exchange depth
  ranks between frames, retain their blur settings, and reopen identically.
  A frame with both effects hidden matches the unmodified rendered background.
- `refraction_existing_compositor_validation.json`: an existing brightness
  adjustment stays after refraction, the original node group remains unchanged,
  and the integrated render reopens identically.
- `refraction_animation_phase_validation.json`: explicit time offsets survive
  FPS/FPS-base changes and native save/reopen.
- `refraction_worker_later_validation.json`: 31-frame diagnostic DMX conversion;
  packed images, frame 31 visibility and installed compositor verified on reopen.
  Render difference from refraction is 0.00304 in the scene camera and 0.06201
  with a fitted camera/checker background (maximum pixel channel difference).
- `refraction_master_timeline_validation.json`: master scene-strip rendering
  matches the direct diagnostic shot at frame 31 exactly. Disabling the shot
  compositor after a fresh reopen removes the measured refraction difference.
  The fresh reopen is necessary to avoid reusing sequencer cached frames.
- `refraction_static_frame_validation.json` and
  `refraction_srgb_tint_texture_render_validation.json`: static regression checks.

These checks do not establish exact SFM visual parity or full-session support.
`maintained_refraction_render_validation.json` verifies five controlled simulator
snapshots using the installed conc_warp material: visible distortion and identical
native reopened render. No installed maintained-count Refract definition was
found in the inventory, so shipped-effect comparison remains unverified.
`moving_maintained_refraction_render_validation.json` also verifies the moving
maintained frame-mesh path renders with conc_warp and reopens identically.
`maintained_refraction_visibility_validation.json` verifies an authored hidden
frame contributes no refraction after reopening, while visible frames still
render the effect. Snapshot evaluation restores the original frame/subframe.
Development failure handling has also been verified by an injected compositor
setup failure through the DMX worker (`refraction_worker_failure_validation.json`).
The result is partial, affected particle records say rendered=false, geometry is
retained in a render-disabled collection, and visibility animation cannot reveal
it after native reopen. This correction is newer than the 0.27.60 package.
Secondary normals, reflection, Source particle draw order, and shot timing need
further integration and comparison before a release can enable this path.

Development support for authored `$ignorez` uses a separate refraction pass scene
so opaque foreground geometry does not occlude that effect. The static authored
material and animated diagnostic checks passed, including hidden frames and
identical renders after native save/reopen. Evidence is in
`refraction_authored_ignore_depth_validation.json` and
`refraction_ignore_depth_animation_validation.json`. This change is newer than
the 0.27.61 package. A diagnostic copy of fireflies.dmx with the installed
blink_dagger_start effect also passed through the conversion worker. Direct shot
and master scene-strip renders match exactly at frames 3, 5, 8, and 13. Disabling
the compositor after reopening changes the frame-5 master render by a maximum
pixel-channel difference of 0.00248855. Evidence is in
`refraction_ignore_depth_master_timeline_validation.json`. Frame 31 has no
refraction geometry because this effect has already ended. The diagnostic
conversion remains partial: some child-effect initializers and operator timing
are unsupported. Other shot transitions and exact Source sorting remain
unverified.

The auxiliary ignore-depth scene copies resolution and frame-rate settings at
conversion time. Blender does not allow drivers on render resolution properties;
changing these settings later requires updating the auxiliary scene as well.
Automatic synchronization of those edits is not implemented. Camera replacement
after conversion also requires updating the auxiliary scene's active camera.

Development also contains a separate delayed-decay clock prototype in
`particle_decay_experimental.py`. It handles a single enabling step, retaining
the original lifetime for appearance while calculating death separately. Three
tests cover early/late births, paused and accelerated clocks, rewinding, and
rejection of unsupported timing ramps. This prototype is not connected to the
conversion worker; engine-tick activation and Source visual behavior remain
unverified. A fourth test verifies default decay matches the existing lifetime
clock, including pauses and variable speed. Native frame geometry visibility
was also verified across 41 samples before and after saving/reopening
(`delayed_decay_native_validation.json`); this is a controlled prototype,
not proof of worker integration or Source parity. The actual frame-mesh bake
function now accepts an explicit development-only `experimental_decay=True`
argument. A controlled definition survives its original lifetime, disappears
at the delayed enabling step, and preserves visibility after native save/reopen
(`delayed_decay_bake_validation.json`). The GUI/worker does not enable this
argument. Default timing validation and rejection remain unchanged when the
experimental option is off.

The installed `blink_dagger_start_smoke` definition also bakes with the explicit
experimental argument: 40 births, 30 frame meshes, and 1,200 quads. A controlled
frame-6 render differs visibly from its particle-hidden background and reopens
identically (`blink_smoke_decay_bake_diagnostic.json`). This verifies native
geometry/rendering for that definition, not exact Source simulation or full
session integration.

Explicit development job JSON can set `experimental_delayed_decay: true`.
A diagnostic Fireflies DMX copy using blink_dagger_start passed through the full
worker with its smoke child now generating native frame meshes, verified after
reopening along with the embedded experimental report flag
(`delayed_decay_worker_validation.json`). The conversion remains partial for
other unsupported children. This job option is not exposed or enabled by the
GUI in release 0.27.62, and does not establish exact SFM timing or visuals.

The same diagnostic worker output has visible smoke contributions from its
converted shot camera at frames 3, 5, 8, and 13. Direct shot and master timeline
renders match exactly at each sample. Hiding only that smoke child's geometry
changes each render, with maximum channel differences from 0.00727 to 0.02660
(`delayed_decay_worker_render_diagnostic.json`). These checks isolate the smoke
contribution; they do not validate its appearance against an SFM render.

The development GUI now exposes **Experimental delayed particle decay**, off
by default. The setting persists and reaches both single and queued jobs.
The GUI startup check and all 204 unit tests pass. Only one enabling step is
supported; timed ramps, oscillating decay, and other unsupported operators still
report limitations. This GUI change is newer than the 0.27.62 release.

An ordinary animated texture-sheet/spin fixture with a default Lifespan Decay
operator produces identical geometry, UV coordinates, and vertex colors with
the delayed-decay option off and on. The enabled result preserves frame
visibility and mesh data after native save/reopen
(`decay_ordinary_bake_regression.json`). This is a targeted regression check,
not an exhaustive test of all installed particles.

Replanning the stored installation inventory found 41 records with a delayed
decay step. Only two duplicate records for `blink_dagger_start_smoke` become
newly accepted by the offline planner; other definitions retain separate
unsupported features. Two records contain unsupported decay timing.
`delayed_decay_inventory_audit.json` includes the inventory SHA-256 and each
remaining blocker. This scan uses the stored inventory and does not prove
native rendering or account for later installation changes.
