"""Numerical Source MDL flex-rule evaluator. No generated script or add-on drivers."""
import math


def target_weight(value, targets):
    """Piecewise linear zero/one/one/zero MDL vertex activation range.

    Valve's studio.h defines the four endpoint weights. This is a native
    interpolation of those endpoints; renderer equivalence remains unverified.
    """
    a,b,c,d = (float(v) for v in targets)
    if not a <= b <= c <= d:
        raise ValueError('MDL flex targets are not ordered')
    if value < a or value > d:
        return 0.
    if value < b:
        return (value-a)/(b-a)
    if value <= c:
        return 1.
    return (d-value)/(d-c) if d > c else 0.


def remap(value,low,high,out_low=0.,out_high=1.):
    factor=(1. if value>=high else 0.) if high==low else max(0.,min(1.,(value-low)/(high-low)))
    return out_low+(out_high-out_low)*factor


def evaluate(mdl, controllers,clamp_controllers=True):
    output=[0.]*len(mdl.flex_names)
    def fetch(index):
        controller=mdl.flex_controllers[int(index)]
        value=float(controllers.get(controller.name,0.))
        return max(controller.min,min(controller.max,value)) if clamp_controllers and controller.min!=controller.max else value
    def normalized(index,low=0.,high=1.):
        c=mdl.flex_controllers[int(index)]
        return remap(fetch(index),c.min,c.max,low,high)
    for rule in mdl.flex_rules:
        stack=[]
        for operation in rule.flex_ops:
            op=int(operation.op); v=operation.value
            if op==1:stack.append(float(v))
            elif op==2:stack.append(fetch(v))
            elif op==3:stack.append(output[int(v)])
            elif op in (4,5,6,7,13,14):
                b,a=stack.pop(),stack.pop()
                stack.append({4:lambda:a+b,5:lambda:a-b,6:lambda:a*b,7:lambda:a/b if b>.0001 else 0.,13:lambda:max(a,b),14:lambda:min(a,b)}[op]())
            elif op==8:stack[-1]=-stack[-1]
            elif op in (10,11,12):continue
            elif op in (18,19):
                n=int(v)
                terms=stack[-n:] if n else []
                if n:del stack[-n:]
                product=math.prod(terms)
                if op==18:stack.append(product)
                else:stack[-1]*=1-product
            elif op==15:stack.append(remap(fetch(v),-1,0,1,0))
            elif op==16:stack.append(remap(fetch(v),0,1))
            elif op==17:
                idx=stack.pop(); w,z,y,x=stack.pop(),stack.pop(),stack.pop(),stack.pop()
                value=fetch(idx)
                ramp=0. if value<=x or value>=w else remap(value,x,y) if value<y else remap(value,z,w,1,0) if value>z else 1.
                stack.append(ramp*fetch(v))
            elif op in (20,21):
                close_index=stack.pop();stack.pop();eye_index=stack.pop()
                close=normalized(close_index);vertical=normalized(v)
                eye=normalized(eye_index,-1,1) if eye_index>=0 else 0.
                stack.append((1-max(0.,eye))*(1-vertical)*close if op==20 else (1+min(0.,eye))*vertical*close)
            else:raise ValueError(f'Unsupported MDL flex operation {op}')
        if len(stack)!=1:raise ValueError('Malformed MDL flex stack')
        output[rule.flex_index]=stack[0]
    return dict(zip(mdl.flex_names,output))
