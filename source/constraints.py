"""Inventory actual constraint operators and their scene dependencies."""
def inventory(root):
    seen=set();operators=[]
    def walk(value):
        if hasattr(value,'type') and hasattr(value,'id'):
            identity=str(value.id)
            if identity in seen:return
            seen.add(identity)
            if 'Constraint' in value.type and value.type not in ('DmeConstraintTarget','DmeConstraintSlave'):
                slave=value.get('slave');slave_target=slave.get('target') if slave is not None else None
                targets=[]
                for target in value.get('targets',[]):
                    dag=target.get('target')
                    targets.append({'element_id':str(target.id),'dag_id':str(dag.id) if dag is not None else None,
                                    'name':dag.name if dag is not None else None,'weight':float(target.get('targetWeight',1.)),
                                    'position_offset':list(target.get('vecOffset',(0,0,0))),
                                    'orientation_offset':list(target.get('oOffset',(0,0,0,1)))})
                joints={}
                for key in ('startJoint','midJoint','endJoint'):
                    joint=value.get(key);dag=joint.get('target') if joint is not None else None
                    if dag is not None:joints[key]={'id':str(dag.id),'name':dag.name}
                operators.append({'id':identity,'name':value.name,'type':value.type,'mode':value.get('mode'),
                                  'slave':{'id':str(slave_target.id),'name':slave_target.name} if slave_target is not None else None,
                                  'targets':targets,'joints':joints,'converted':False})
            for child in value.values():walk(child)
        elif isinstance(value,(list,tuple)):
            for child in value:walk(child)
    walk(root)
    return operators


def bake(shot,objects,frames,seconds,transform,axis,curves,progress=None):
    """Bake point/orient and pole-controlled two-bone IK in Source space."""
    from mathutils import Matrix,Vector,Quaternion
    import numpy as np
    import bpy
    nodes={};parents={}
    def collect(dag,parent=None):
        if dag is None or str(dag.id) in nodes:return
        key=str(dag.id);nodes[key]=dag;parents[key]=parent
        for child in dag.get('children',[]):collect(child,key)
    collect(shot.element.get('scene'))
    elements={}
    def references(value):
        if hasattr(value,'id'):
            key=str(value.id)
            if key in elements:return
            elements[key]=value
            for child in value.values():references(child)
        elif isinstance(value,(list,tuple)):
            for child in value:references(child)
    references(shot.element)
    records=inventory(shot.element);supported={};by_slave={}
    for record in records:
        reason=None;operator=elements[record['id']]
        ik=record['type']=='DmeRigIKConstraintOperator'
        if record['type'] not in ('DmeRigPointConstraintOperator','DmeRigOrientConstraintOperator','DmeRigIKConstraintOperator'):reason='Constraint solver not implemented for this operator type'
        elif len(record['targets'])!=1 or (not record['slave'] and not ik):reason='Requires a single target and a slave DAG'
        else:
            slave=record.get('joints',{}).get('startJoint',{}).get('id') if ik else record['slave']['id']
            target=record['targets'][0]['dag_id'];entry=operator['targets'][0]
            if slave not in nodes or target not in nodes:reason='Target or slave is outside the imported scene DAG'
            elif any(int(shot.value(operator,'mode',t,0))!=0 for t in seconds):reason='Constraint operator mode is unsupported'
            elif any(abs(float(shot.value(entry,'targetWeight',t,1.))-1.)>1e-6 for t in seconds):reason='Weighted constraint blending is not implemented'
            else:
                for t in seconds:
                    pos=shot.value(entry,'vecOffset',t,(0,0,0));rot=shot.value(entry,'oOffset',t,(0,0,0,1))
                    point=record['type']=='DmeRigPointConstraintOperator'
                    positional=any(abs(float(v))>1e-6 for v in pos)
                    rotational=any(abs(float(v))>1e-6 for v in rot[:3]) or abs(abs(float(rot[3]))-1)>1e-6
                    nonzero=(positional or rotational) if ik else positional if point else rotational
                    if nonzero:
                        reason='Nonzero constraint offsets require verified Source evaluation';break
            if not reason and ik:
                joint_ids=[record.get('joints',{}).get(k,{}).get('id') for k in ('startJoint','midJoint','endJoint')]
                pole=operator.get('pvTarget');pole_id=str(pole.id) if pole is not None else None
                if any(j not in nodes for j in joint_ids) or pole_id not in nodes:reason='IK requires three imported joints and an imported pole target'
                elif parents[joint_ids[1]]!=joint_ids[0] or parents[joint_ids[2]]!=joint_ids[1]:reason='IK joints must form a direct two-bone chain'
                else:
                    record['ik_joint_ids']=joint_ids;record['pole_id']=pole_id;record['clamped_frames']=0
        if reason:record['reason']=reason
        else:
            supported[record['id']]=record
            for affected in record['ik_joint_ids'] if ik else [slave]:by_slave.setdefault(affected,[]).append(record)
    conflicts=set()
    for slave,items in by_slave.items():
        for operator_type in ('DmeRigPointConstraintOperator','DmeRigOrientConstraintOperator'):
            competing=[record for record in items if record['type']==operator_type]
            if len(competing)>1:
                for record in competing:
                    record['reason']='Overlapping constraints drive the same transform component; Source solver ordering is not implemented'
                    conflicts.add(record['id'])
    for identity in conflicts:del supported[identity]
    by_slave={key:[record for record in items if record['id'] not in conflicts] for key,items in by_slave.items()}
    for record in list(supported.values()):
        if record['type']!='DmeRigIKConstraintOperator':continue
        start,mid,end=record['ik_joint_ids'];conflict=False
        for joint in (start,mid,end):
            for other in by_slave.get(joint,[]):
                if other is record:continue
                if joint!=end or other['type']!='DmeRigOrientConstraintOperator':conflict=True
        if conflict:
            record['reason']='IK chain overlaps another positional or joint-orientation solver'
            del supported[record['id']]
            for joint in (start,mid,end):by_slave[joint]=[r for r in by_slave[joint] if r is not record]
    by_slave={k:v for k,v in by_slave.items() if v}
    # IK supplies joint orientations; explicit end-joint orientation constraints
    # then preserve the animator's wrist/ankle controls.
    for key,items in by_slave.items():
        items.sort(key=lambda r:r['type']!='DmeRigIKConstraintOperator')
    # Solve in dependency order rather than applying operators in file order.
    order=[];visiting=set();visited=set()
    def visit(key):
        if key in visiting:raise ValueError('Cyclic constraint/parent dependencies')
        if key in visited:return
        visiting.add(key)
        if parents[key] is not None:visit(parents[key])
        for record in by_slave.get(key,[]):visit(record['targets'][0]['dag_id'])
        for record in by_slave.get(key,[]):
            if record['type']=='DmeRigIKConstraintOperator':visit(record['pole_id'])
        visiting.remove(key);visited.add(key);order.append(key)
    try:
        for key in nodes:visit(key)
    except ValueError as exc:
        for record in supported.values():record['reason']=str(exc)
        return records
    if not supported:return records
    world_samples=[];rows={key:[] for key in by_slave}
    for sample_index,t in enumerate(seconds):
        if progress and (sample_index%100==0 or sample_index==len(seconds)-1):
            progress(f'Rig constraints: frame {sample_index+1}/{len(seconds)}')
        world={};ik_results={}
        for key in order:
            parent=parents[key];local=transform(shot,nodes[key].get('transform'),t)
            matrix=world[parent]@local if parent is not None else local
            for record in by_slave.get(key,[]):
                target=world[record['targets'][0]['dag_id']]
                p,q,s=matrix.decompose()
                if record['type']=='DmeRigPointConstraintOperator':p=target.translation
                elif record['type']=='DmeRigOrientConstraintOperator':q=target.to_quaternion()
                else:
                    from ik import solve
                    start,mid,end=record['ik_joint_ids']
                    if record['id'] not in ik_results:
                        mid_matrix=matrix@transform(shot,nodes[mid].get('transform'),t)
                        end_matrix=mid_matrix@transform(shot,nodes[end].get('transform'),t)
                        solved=solve(tuple(p),tuple(mid_matrix.translation),tuple(end_matrix.translation),tuple(target.translation),tuple(world[record['pole_id']].translation))
                        end_pos=Vector(solved['end']);mid_pos=Vector(solved['knee'])
                        normal=-(end_pos-p).normalized().cross(Vector(solved['bend_direction'])).normalized()
                        def orientation(a,b,offset_key):
                            x=(b-a).normalized();y=normal;z=x.cross(y).normalized();y=z.cross(x).normalized()
                            aim=Matrix((x,y,z)).transposed().to_quaternion()
                            offset=shot.value(elements[record['id']],offset_key,t,(0,0,0,1))
                            return aim@Quaternion((offset[3],*offset[:3])).normalized()
                        ik_results[record['id']]={start:(p,orientation(p,mid_pos,'startOffset')),mid:(mid_pos,orientation(mid_pos,end_pos,'midOffset')),end:(end_pos,None)}
                        record['clamped_frames']+=int(solved['clamped'])
                    p,rotation=ik_results[record['id']][key]
                    if rotation is not None:q=rotation
                matrix=Matrix.LocRotScale(p,q,s)
            world[key]=matrix
            if key in rows:
                local=world[parent].inverted_safe()@matrix if parent is not None else matrix
                if nodes[key].type in ('DmeCamera','DmeProjectedLight'):local=local@axis
                p,q,s=local.decompose();rows[key].append([*p,*q,*s])
        world_samples.append(world)
    actions={}
    def write(owner,path,values,name):
        values=np.array(values);previous=None
        for row in values:
            q=Quaternion(row[3:7])
            if previous is not None and previous.dot(q)<0:q.negate();row[3:7]=q
            previous=q.copy()
        action=actions.get(owner)
        if action is None:
            previous_action=owner.animation_data.action if owner.animation_data else None
            action=actions[owner]=curves(owner,name)
            # The evaluated bake replaces this owner's raw log action. Release
            # it only when no object or retained user still references it.
            if previous_action is not None and previous_action.users==0:
                bpy.data.actions.remove(previous_action)
        action.add(path('location'),frames,values[:,:3]);action.add(path('rotation_quaternion'),frames,values[:,3:7]);action.add(path('scale'),frames,values[:,7:])
    for key,values in rows.items():
        obj=objects[key];obj.rotation_mode='QUATERNION'
        write(obj,lambda p:p,values,obj.name+' constraint bake')
    # Bake resulting Source joint world matrices back into the actual armature,
    # not just the DAG proxy objects used for rig/attachment evaluation.
    for key,dag in nodes.items():
        if dag.type!='DmeGameModel' or key not in objects:continue
        arm=next((o for o in objects[key].children if o.type=='ARMATURE'),None)
        if arm is None:
            pivot=next((o for o in objects[key].children if o.get('sfm_bone_transform')),None)
            if pivot is not None:
                joint_id=next((joint_id for joint_id,joint in nodes.items() if str(getattr(joint.get('transform'),'id',''))==pivot['sfm_bone_transform']),None)
                if joint_id is not None:
                    flat=list(pivot['sfm_rest_inverse']);rest=Matrix([flat[i:i+4] for i in range(0,16,4)])
                    values=[]
                    for world in world_samples:
                        desired=rest@world[key].inverted_safe()@world[joint_id]
                        p,q,s=desired.decompose();values.append([*p,*q,*s])
                    write(pivot,lambda p:p,values,pivot.name+' constraint bake')
            continue
        transforms={str(bt.id):bt for bt in dag.get('bones',[])}
        bindings={}
        import re
        for joint_id,joint in nodes.items():
            bt=transforms.get(str(getattr(joint.get('transform'),'id','')))
            if bt is None:continue
            match=re.match(r'bone\s+\d+\s+\((.*)\)',bt.name);name=(match.group(1) if match else bt.name)[:63]
            if name in arm.pose.bones:bindings[name]=joint_id
        for name,joint_id in bindings.items():
            bone=arm.data.bones[name];rest=bone.matrix_local
            if bone.parent:rest=bone.parent.matrix_local.inverted_safe()@rest
            values=[]
            for world in world_samples:
                desired=world[key].inverted_safe()@world[joint_id]
                if bone.parent and bone.parent.name in bindings:
                    parent=world[key].inverted_safe()@world[bindings[bone.parent.name]]
                    desired=parent.inverted_safe()@desired
                p,q,s=(rest.inverted_safe()@desired).decompose();values.append([*p,*q,*s])
            pb=arm.pose.bones[name];pb.rotation_mode='QUATERNION'
            write(arm,pb.path_from_id,values,arm.name+' constrained bones')
    for record in supported.values():record['converted']=True;record['method']='native sampled transform bake'
    return records
