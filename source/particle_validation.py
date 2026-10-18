"""Describe bake evidence without claiming that a final image was rendered."""
def converted(record):
    """Simulation-only controllers can succeed without producing geometry."""
    return not record.get('reason') and bool(record.get('rendered') or
        (record.get('simulation_only') and record.get('simulated')))

def annotate(record):
    if not converted(record):
        state='conversion_failed'
    elif record.get('simulation_only'):
        state='parent_simulation_baked'
    elif record.get('visible_sample_count')==0:
        state='hidden_at_requested_samples'
    elif record.get('renderable_geometry_generated'):
        state='nondegenerate_geometry_baked'
    elif record.get('geometry_generated'):
        state='geometry_baked_renderability_unverified'
    else:
        state='no_geometry_at_requested_samples'
    record['validation']={'stage':state,'final_image_render_verified':False,
                          'source_visual_parity_verified':False,
                          'scope':'Requested bake samples only; rendered is a legacy conversion-status field'}
    return record
