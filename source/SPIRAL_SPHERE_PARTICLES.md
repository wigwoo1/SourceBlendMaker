Development support for Position On Spiral Sphere follows installed initializer
0x102045c0. Its constants are 2/density, height 1 - half the height step, and
angle step (3 - sqrt(5)) * pi. The installed counter resets only when greater
than density. A boundary point can therefore exceed the nominal radius.

The baker applies birth control-point rotation and translation and supports
zero initial speed, fixed density, no CP scaling override, and inactive shared
random seeds without strength fades. Other settings are rejected explicitly.
Source uses mutable float counters; development uses algebraic counters based
on particle birth index. Effect restarts, tick phase, float/trig rounding and
random-stream ordering are not proven equivalent and are reported as limits.

Three arithmetic tests pass. The original I dunno_copy_copy3 effect in
particle test.dmx passed native save/reopen validation of 63 sampled meshes
with all modules and parameters retained. A fitted-camera Cycles sample at
frame 60 visibly renders the particle effect. This is an isolated effect test,
not a full-session comparison to SFM. This feature is not in released version
0.27.82.
