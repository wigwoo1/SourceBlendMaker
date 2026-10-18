# Epitrochoid position initializer

Development support converts Position Along Epitrochoid for creation-time phase,
zero shared random seeds with no shared strength fades, no CP radius override, and no composition
with existing particle positions. CP translation is sampled at birth by the baker;
local-space curve offsets use the CP rotation. Dimension -1 disables a component.

Installed initializer 0x10205320 uses total radius R+r and adds both trigonometric
terms. Its denominator includes 2^-23. Static trig-table inspection confirms the
cosine and sine helper identities without loading or executing the SFM DLL.
Python floating-point/trig and offline birth timing remain approximations.

The authored I dunno_copy effect in particle test.dmx has nondefault time and
strength ranges but zero seeds. Static metadata maps the seeds to offsets 0x30
and 0x24. Shared gate 0x101ebe20 tests those seeds before sampling ranges;
zero seeds leave those ranges inactive. Development accepts this case without
changing the authored parameters. Nonzero seeds and shared fades remain
unsupported. Counter-based phase is also
rejected until Source context resets are reproduced.

Five targeted unit tests pass, including planner CP selection and nonmutation.
An isolated native Blender test saved and reopened the curve with its authored
plane force and both lifetime initializers. That test removed Color Fade and
overrode the four shared time/strength scales to 1. It does not establish full
authored-effect fidelity. Latest shipped version remains 0.27.81; curve support
is development work and is not included in that release.

Native attempts on the authored effect exposed two additional blockers: its
Force based on distance from plane module is unsupported, and it has two Lifetime
Random initializers (authored maxima 7 and approximately 0.4). Even an isolated
attempt with the force removed originally failed the single-lifetime gate.
Development now samples repeated Lifetime Random settings in order, retaining
earlier random draws and using the final lifetime. Source random-stream parity
and ordering relative to other initializer types remain approximate. With that
gate resolved, development also handles the authored plane-distance force with
an approximate 120 Hz integration step.

Static inspection of installed Color Fade and Color Light from Control Point
operators shows that fade reads the birth-color stream, while lighting reads the
current-color stream. Development preserves their authored RGB write order.
Lighting uses the sampled particle position, so operator-time position history
and Source color-space parity remain unverified. A native test retaining both
color operators saved and reopened 63 frame meshes with finite vertices and
particle-color attributes. All authored modules were retained, but the four
shared curve time/strength scales were still overridden to 1. Tests do not
modify source sessions or PCF assets.

A subsequent test retained every authored module and parameter of I dunno_copy,
including its inactive scale ranges. It saved and reopened 63 sampled frame
meshes with finite coordinates and color attributes. Geometry and color hashes
matched the earlier override test, confirming that these zero-seed ranges do
not change this implementation's output. This is one effect, not a full-session
or all-particle validation. Source tick timing, random streams and visual parity
remain approximate. This development support is not yet in release 0.27.82.
