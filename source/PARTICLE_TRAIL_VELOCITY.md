# Velocity fallback for static sprite trails

The particle baker normally determines a sprite trail from the particle's
position at the current sample and at the trail lookback time. Some installed
Source particle definitions provide an initial velocity but omit a `Movement
Basic` operator. In that case the converter's position history can remain
static even though the trail renderer has a nonzero velocity to follow.

For unlocked particles only, when sampled displacement is zero, the converter
estimates trail displacement as initial velocity multiplied by
`min(particle age, trail duration)`. The renderer's maximum length and fade-in
still apply. A trail with zero length or zero width is omitted rather than
saved as a degenerate face. Existing sampled motion takes precedence.

This is an approximation of Source particle integration and trail timing; it
does not establish exact SFM tick, random-stream, or visual parity. Locked
control-point trails continue to use sampled control transforms and do not use
this fallback.
