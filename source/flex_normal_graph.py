"""Native graph for weighted authored-normal transformation."""
import numpy as np,json

def transform(graph,source,weights,matrices,frames,armature=None,bone_names=None):
    total=None
    for index,(weight,samples) in enumerate(zip(weights,matrices)):
        rows=[]
        for row in range(3):
            vector=graph.nodes.new('ShaderNodeCombineXYZ')
            for frame,matrix in zip(frames,samples):
                for col,socket in enumerate(vector.inputs):
                    socket.default_value=float(matrix[row][col]);socket.keyframe_insert('default_value',frame=frame)
            if armature is not None:
                name=bone_names[index];rest_inverse=armature.data.bones[name].matrix_local.inverted().to_3x3()
                for col,socket in enumerate(vector.inputs):
                    driver=socket.driver_add('default_value').driver;terms=[]
                    for axis in range(3):
                        variable=driver.variables.new();variable.name='p'+str(axis);variable.type='SINGLE_PROP'
                        variable.targets[0].id=armature;variable.targets[0].data_path='pose.bones['+json.dumps(name)+'].matrix['+str(axis)+']['+str(row)+']'
                        terms.append(variable.name+'*'+repr(float(rest_inverse[axis][col])))
                    driver.expression='+'.join(terms)
            dot=graph.nodes.new('ShaderNodeVectorMath');dot.operation='DOT_PRODUCT'
            graph.links.new(source,dot.inputs[0]);graph.links.new(vector.outputs[0],dot.inputs[1]);rows.append(dot.outputs['Value'])
        vector=graph.nodes.new('ShaderNodeCombineXYZ')
        for row,field in enumerate(rows):graph.links.new(field,vector.inputs[row])
        scale=graph.nodes.new('ShaderNodeVectorMath');scale.operation='SCALE';graph.links.new(vector.outputs[0],scale.inputs[0])
        if isinstance(weight,(float,int)):scale.inputs['Scale'].default_value=weight
        else:graph.links.new(weight,scale.inputs['Scale'])
        result=scale.outputs['Vector']
        if total is None:total=result
        else:
            add=graph.nodes.new('ShaderNodeVectorMath');add.operation='ADD';graph.links.new(total,add.inputs[0]);graph.links.new(result,add.inputs[1]);total=add.outputs['Vector']
    if total is None:raise ValueError('No weighted bone normals')
    normalize=graph.nodes.new('ShaderNodeVectorMath');normalize.operation='NORMALIZE';graph.links.new(total,normalize.inputs[0]);return normalize.outputs['Vector']
