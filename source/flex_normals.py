"""Compiled normal deltas using native fields and evaluated bone matrices."""
import bpy,numpy as np,json

def install(obj,base,deltas,metadata,armature=None):
    graph=bpy.data.node_groups.new(obj.name+' compiled flex normals','GeometryNodeTree')
    graph.interface.new_socket(name='Geometry',in_out='INPUT',socket_type='NodeSocketGeometry')
    graph.interface.new_socket(name='Geometry',in_out='OUTPUT',socket_type='NodeSocketGeometry')
    input=graph.nodes.new('NodeGroupInput');output=graph.nodes.new('NodeGroupOutput')
    def attribute(name,values):
        attr=obj.data.attributes.new(name,'FLOAT_VECTOR','POINT');attr.data.foreach_set('vector',np.asarray(values,dtype=np.float32).ravel())
        node=graph.nodes.new('GeometryNodeInputNamedAttribute');node.data_type='FLOAT_VECTOR';node.inputs['Name'].default_value=attr.name
        return node.outputs['Attribute']
    total=attribute('sbm_base_normal',base)
    for index,(key_name,entry) in enumerate(metadata.items()):
        delta=deltas.get((entry['source_flex'],tuple(entry['targets'])))
        if delta is None or not np.any(delta):continue
        field=attribute('sbm_flex_normal_'+str(index),delta)
        weight=graph.nodes.new('ShaderNodeValue');driver=weight.outputs[0].driver_add('default_value').driver
        variable=driver.variables.new();variable.name='weight';variable.type='SINGLE_PROP'
        variable.targets[0].id_type='KEY';variable.targets[0].id=obj.data.shape_keys
        variable.targets[0].data_path=obj.data.shape_keys.key_blocks[key_name].path_from_id('value');driver.expression='weight'
        scale=graph.nodes.new('ShaderNodeVectorMath');scale.operation='SCALE';graph.links.new(field,scale.inputs[0]);graph.links.new(weight.outputs[0],scale.inputs['Scale'])
        add=graph.nodes.new('ShaderNodeVectorMath');add.operation='ADD';graph.links.new(total,add.inputs[0]);graph.links.new(scale.outputs['Vector'],add.inputs[1]);total=add.outputs['Vector']
    normalize=graph.nodes.new('ShaderNodeVectorMath');normalize.operation='NORMALIZE';graph.links.new(total,normalize.inputs[0])
    field=normalize.outputs['Vector']
    if armature is not None:
        from flex_normal_graph import transform
        names=[];fields=[]
        for group in obj.vertex_groups:
            if group.name not in armature.data.bones:continue
            weights=np.zeros(len(obj.data.vertices),dtype=np.float32)
            for vertex in obj.data.vertices:
                for item in vertex.groups:
                    if item.group==group.index:weights[vertex.index]=item.weight
            if not np.any(weights):continue
            attr=obj.data.attributes.new('sbm_normal_bone_'+str(group.index),'FLOAT','POINT');attr.data.foreach_set('value',weights)
            node=graph.nodes.new('GeometryNodeInputNamedAttribute');node.data_type='FLOAT';node.inputs['Name'].default_value=attr.name;fields.append(node.outputs['Attribute']);names.append(group.name)
        field=transform(graph,field,fields,[[] for name in names],[],armature=armature,bone_names=names)
    normal=graph.nodes.new('GeometryNodeSetMeshNormal');normal.mode='FREE' if armature is not None else 'TANGENT_SPACE';normal.domain='POINT'
    graph.links.new(input.outputs['Geometry'],normal.inputs['Mesh']);graph.links.new(field,normal.inputs['Custom Normal']);graph.links.new(normal.outputs['Mesh'],output.inputs['Geometry'])
    modifier=obj.modifiers.new('Source flex normals','NODES');modifier.node_group=graph
    if armature is None:obj.modifiers.move(len(obj.modifiers)-1,0)
    return graph

def attach(assets,mdl,container,relative_path):
    """Attach normals to importer-mapped LOD0 meshes; reject mismatched mapping."""
    from SourceIO.library.models.vvd import Vvd
    from SourceIO.library.models.vtx.v7.vtx import Vtx
    from SourceIO.library.utils.common import get_slice
    from SourceIO.blender_bindings.models.common import merge_meshes
    if int(mdl.header.version) != 49:
        raise ValueError('Compiled flex normals currently validated for MDL49 only')
    vvd=Vvd.from_buffer(assets.buffer(relative_path[:-4]+'.vvd'))
    vtx=Vtx.from_buffer(assets.buffer(relative_path[:-4]+'.dx90.vtx'))
    meshes=iter(o for o in container.objects if o.type=='MESH');plans=[]
    for body,vbody in zip(mdl.body_parts,vtx.body_parts):
        for model,vmodel in zip(body.models,vbody.models):
            if not model.vertex_count:continue
            obj=next(meshes)
            if not obj.data.shape_keys:continue
            metadata=json.loads(obj.get('sfm_flex_target_ranges','{}'))
            if not metadata:raise ValueError('Compiled flex normal mapping metadata missing')
            indices,*_=merge_meshes(model,vmodel.model_lods[0])
            if len(obj.data.vertices)!=len(indices):raise ValueError('Compiled flex normal vertex mapping differs')
            deltas={}
            for mesh in model.meshes:
                for flex in mesh.flexes:
                    raw=flex.vertex_animations
                    if raw is None or 'normal_delta' not in raw.dtype.names:continue
                    contributions=[(mdl.flex_names[flex.flex_desc_index],np.ones(len(raw)))]
                    if flex.partner_index:
                        side=raw['side'].reshape(-1)/255.
                        contributions=[(mdl.flex_names[flex.flex_desc_index],1.-side),(mdl.flex_names[flex.partner_index],side)]
                    for name,balance in contributions:
                        delta=deltas.setdefault((name,tuple(flex.targets)),np.zeros((model.vertex_count,3)))
                        np.add.at(delta,raw['index'].reshape(-1)+mesh.vertex_index_start,raw['normal_delta']*balance[:,None])
            mapped={key:values[indices] for key,values in deltas.items()}
            if not any(np.any(value) for value in mapped.values()):continue
            base=get_slice(vvd.lod_data[0],model.vertex_offset,model.vertex_count)['normal'][indices]
            arm=next((m.object for m in obj.modifiers if m.type=='ARMATURE'),None)
            plans.append((obj,base,mapped,metadata,arm))
    if not plans:raise ValueError('No mapped nonzero compiled normal deltas')
    rows=[]
    for obj,base,deltas,metadata,arm in plans:
        # Static flex meshes need free normals as well; avoid tangent encoding.
        graph=install(obj,base,deltas,metadata,armature=arm)
        if arm is None:graph.nodes['Set Mesh Normal'].mode='FREE'
        rows.append({'mesh':obj.name,'vertices':len(base),'native_nodes':len(graph.nodes),'bone_matrix_drivers':arm is not None})
    return rows
