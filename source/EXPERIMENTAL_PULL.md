# Experimental particle pull forces

The GUI includes an optional **Experimental particle pull forces** checkbox. It is off by default. This option is included starting with release 0.27.65.

When enabled, supported sprite and trail effects can bake one nonlocal `Pull towards control point` force against an animated imported control point. The converter samples the target using the effect's simulation clock and restores the scene time after historical queries. Random forces, gravity, and basic movement drag can participate in the approximation. Baked geometry is stored in the Blender file.

Version 0.28.2 uses cached ordered position-buffer movement at 120 Hz when the effect has one Movement Basic operator and drag between 0 and 0.9999. Pull, world-axis twist, random forces, gravity, and position oscillation then participate in the same movement history. Other previously accepted drag settings retain the older midpoint approximation.

Source simulation ticks, random-number sequences, and visual trajectory equivalence have not been verified. Paused-clock boundary ownership is also an approximation. This option does not guarantee that an entire particle system will import: its other operators, initializers, renderers, materials, and control points must also be supported.

The converter rejects multiple pull forces, local-space pull, magnitude control-point scaling, nondefault shared force timing or strength settings, unsupported combined forces, and movement-lock combinations. Rejected effects remain identified in the conversion report instead of silently discarding those settings.

Validation includes an isolated installed aura definition with an animated control point and five baked sample frames. An actual Pokémon session preview at frames 9085–9096 also saved and reopened: five pull effect types produced 54 nonempty frame meshes with finite coordinates. An isolated render at frame 9090 visibly shows aura geometry using a fitted diagnostic camera. The packed fireball texture was checked byte for byte. These checks do not compare appearance or trajectories against SFM. The preview's overall conversion status is partial because other effects remain unsupported; the complete animation has not been validated.

Diagnostic jobs can specify `preview_frames` and `preview_start_frame` to sample a short range without changing the original shot clock. These are developer job fields, not public GUI controls. A short preview does not validate the complete animation.

Preview scene animation keys cover only the requested range. Particle birth-history queries outside that range may therefore use clamped imported transforms. The actual-session preview proves generated geometry and native renderability, but does not validate historical control-point motion. Ordinary full conversions key the full shot. Current development reports explicitly label this diagnostic limitation.

An additional 0.27.92 development check imported control-point and camera keys over the entire shot before baking selected aura definitions from `particle test.dmx`. It produced 65 finite particle meshes and saved/reopened successfully with authored modules retained. This removes the short-preview transform-clamping limitation for that test, but does not establish Source simulation timing, trajectory parity, whole-session coverage, or a packaged GUI conversion.
