"""Separate BSP sky faces without rebuilding their UVs or material slots."""
import bpy
import bmesh
from mathutils import Matrix,Vector

def apply_camera_transform(obj,camera,unit_scale):
    """Inverse of Source's sky view origin = main origin / scale + sky origin."""
    scale=float(camera.get('scale',16.))
    if scale<=0:scale=1.
    origin=Vector(tuple(float(v)*unit_scale for v in camera['origin'].split()))
    obj.matrix_world=Matrix.Scale(scale,4)@Matrix.Translation(-origin)@obj.matrix_world
    obj['sfm_sky_scale']=scale
    obj['sfm_sky_origin']=list(origin)
    obj['sfm_sky_camera_angles']=str(camera.get('angles','0 0 0'))
    return scale

def split_faces(obj,face_ids):
    attribute=obj.data.attributes.get('sfm_bsp_face_id')
    if attribute is None:return None
    selected=set(face_ids)
    if not any(item.value in selected for item in attribute.data):return None
    sky=obj.copy();sky.data=obj.data.copy();sky.name=obj.name+' 3D sky geometry'
    for collection in obj.users_collection:collection.objects.link(sky)
    def retain(mesh,keep_selected):
        bm=bmesh.new()
        try:
            bm.from_mesh(mesh)
            ids=bm.faces.layers.int['sfm_bsp_face_id']
            unwanted=[face for face in bm.faces if (face[ids] in selected)!=keep_selected]
            bmesh.ops.delete(bm,geom=unwanted,context='FACES_ONLY')
            loose=[vertex for vertex in bm.verts if not vertex.link_faces]
            bmesh.ops.delete(bm,geom=loose,context='VERTS')
            bm.to_mesh(mesh);mesh.update()
        finally:bm.free()
    retain(sky.data,True);retain(obj.data,False)
    sky['sfm_3d_sky_geometry']=True
    return sky
