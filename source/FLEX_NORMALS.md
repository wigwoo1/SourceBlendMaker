# Compiled facial flex normals

SourceBlendMaker imports nonzero compiled normal deltas for supported MDL49 flex meshes. Each imported mesh stores base and flex normal fields, uses the existing animated shape weights for activation and stereo balance, and transforms the result through evaluated pose matrices and inverse bone rest transforms. Native arithmetic drivers and geometry nodes evaluate in Blender without an external add-on or runtime script. Normals are applied after armature deformation using free-normal storage, avoiding tangent-normal collapse on degenerate faces.

Validated with the installed Nova model from Peaches and the installed HWM Engineer. Peaches passes independently reconstructed normal and bone-weight comparisons, native save/reopen, controlled Cycles normal-render comparison, and complete-session conversion. Engineer passes compiled-normal comparisons with controlled paired-shape weights. These checks do not prove exact SFM expressions or beauty-render appearance.

Other MDL formats remain explicitly unconverted in the report. Nonrigid bone scaling, additional user modifiers that change topology, and all installed model variants have not been validated. Delayed flex vertex history remains a separate reported limitation. Existing image normal maps and material overrides are preserved independently of these mesh normal fields.

The graph adds attributes and drivers, so files and evaluation can grow for models with many facial shapes. Individual records appear under `flex_normal_deltas` in the conversion report. A failed mapping retains a clear warning and an unconverted record rather than claiming complete normal support.
