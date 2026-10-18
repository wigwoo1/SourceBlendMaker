# Control-point color initialization

`Remap Control Point to Vector` can initialize RGB field 6 from the three
components of an imported control point. The converter reads those components
in Source units, remaps each through the authored input and output bounds,
optionally multiplies the existing particle color, and clamps RGB to 0–1.
The output is linear RGB; it is not treated as 0–255 color data.

This initializer runs in SFM's second initialization pass, after ordinary
`Color Random` initialization, even if it appears earlier in the PCF list.
Multiple supported remaps retain their authored order. Each particle keeps
its birth color when the control point changes later. Supported creation-time
gates use `[start,end)`; either endpoint equal to `-1` disables the whole gate,
matching the installed scalar implementation.

All input and output bounds default to `(0,0,0)`. The default output field is
position, not RGB, so this feature requires an explicit RGB field selection.
Position/other-field writes, local-space bound transforms, and nondefault
shared operator strength/time gates remain unsupported and are reported.
Missing imported control points are reported rather than replaced with a
guessed color.

Birth-time control-point queries approximate SFM's emission-batch timing.
Exact Source random streams, engine tick phase, and visual parity are not
claimed. Diagnostic tests use original installed laser-dot, killstreak-glow,
and paint-stream definitions with explicit animated control-point bindings;
they do not verify the original authored sessions for those effects.
