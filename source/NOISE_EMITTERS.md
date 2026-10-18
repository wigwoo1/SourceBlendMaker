# Noise-emitted particles

`emit noise` now uses a scalar port of the installed SFM PET lookup-table
noise function. Authored minimum/maximum emission rates, time coordinate
scale/offset, absolute/inverted noise, start time and duration are preserved.
Particle births use an approximate 120 Hz offline clock and floor accumulated
emission; Source tick phase and random-stream parity are not verified.

The original `final_flash1_electric1` effect in `particle test.dmx` produced
126 sampled native meshes, passed save/reopen checks, and rendered visibly
with its original `effects/sc_electric1.vmt` material. This is an isolated
effect test, not proof of full-scene or live-SFM visual parity.

World-time random coordinates, control-point/parent emission scaling, and
emitter strength fades remain explicitly unsupported for noise emitters.
The lookup tables were inspected statically from the installed PET binary
SHA256 `340b0278d7258015a1bd9fd6cc4068d593469dee999eec15667f85a776f5e506`.
No SFM DLL code is loaded or executed by conversion.

# Imported volumetric beams

On Blender versions exposing `cycles.volume_biased`, scenes with imported
SFM beam cones select biased volume sampling. In the tested overlapping beams
in `reverse psycology.blend`, this avoided the severe grain and denoising
blotches observed with unbiased sampling. Beams and their animations remain.
Scenes without imported beam cones retain their renderer settings. This is
a renderer sampling choice, not a claim of exact SFM volumetric appearance.
