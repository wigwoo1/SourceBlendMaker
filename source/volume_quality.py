"""Render sampling for homogeneous imported SFM beam volumes."""

def configure_beam_sampling(scene):
    # Blender 5 introduced unbiased volume sampling. In the tested overlapping
    # Source beam cones this produced severe noise even at 512 samples, whereas
    # the legacy biased integrator converged cleanly at 64. Keep this choice
    # scoped to scenes containing imported beams; do not change particle media.
    if not hasattr(scene.cycles, 'volume_biased'):
        return False
    scene.cycles.volume_biased = True
    scene['sfm_beam_volume_sampling'] = 'BIASED'
    return True
