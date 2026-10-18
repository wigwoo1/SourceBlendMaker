"""Exclude completed frame sprites while sampling animated controls.

Only sprite-only scene-root collections are detached. Mixed collections and
control hierarchies remain active, and all links are restored on exceptions.
"""
from contextlib import contextmanager

@contextmanager
def suspend_completed_sprites(scene):
    detached = []
    try:
        for collection in list(scene.collection.children):
            objects = list(collection.objects)
            if collection.children or not objects:
                continue
            if not all(o.type == 'MESH' and o.get('sfm_baked_particle_effect')
                       and o.get('sfm_baked_frame') is not None for o in objects):
                continue
            scene.collection.children.unlink(collection)
            detached.append(collection)
        yield len(detached)
    finally:
        for collection in detached:
            if collection.name not in scene.collection.children:
                scene.collection.children.link(collection)
