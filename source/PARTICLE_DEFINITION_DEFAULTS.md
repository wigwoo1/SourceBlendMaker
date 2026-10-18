# Particle definition lifetime

If an effect has no enabled `Lifetime Random` initializer, the converter uses
the particle definition's `lifetime` value. The installed SFM default is one
second. This constant does not consume a lifetime random sample.

An enabled lifetime initializer overrides the definition value. Its own omitted
minimum and maximum values default to zero; it does not inherit the definition's
one-second default. Sequence-derived lifetime is handled separately when a
supported texture sheet and sequence timing are available.

The conversion report records `definition_lifetime` when this fallback is used.
Nonfinite, negative, or zero effective lifetime ranges remain unsupported.
Other operators, renderers, materials, and model bindings still need to pass
their normal conversion checks.

For `Oscillate Scalar`, omitted fields now use the serialized values found in
other installed copies of the same Source-authored effects: field 7 (alpha),
proportional flags enabled, start/end window 0–1, multiplier 2, and phase 0.5.
The matching smoke and ember variants pass isolated Blender bake, save/reopen,
and visible diagnostic-render tests. This default recovery does not establish
Source visual parity or exact particle timing.

For continuous emitters, `emission_duration = -1` is treated as no duration
cutoff. This sentinel is present in the installed Portal 2 `robot_fx.pcf`
definitions; five affected ring/light effects now pass isolated visible-render
and save/reopen tests.

Static inspection of the installed `pet.dll` links the definition unpack entry
`lifetime`, default string `1.0`, and member offset `0x3ac` to the collection's
initial lifetime-field writes. No DLL code was executed for this inspection.
The diagnostic original `burningplayer_rainbow_stroke` definition is tested on
an animated benchmark model binding; this is not a claim of exact SFM visual
parity or validation of its original authored session.
