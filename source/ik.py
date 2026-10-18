"""Two-bone geometric solve, independent of SFM's joint rotation conventions."""
import math

def add(a,b):return tuple(x+y for x,y in zip(a,b))
def sub(a,b):return tuple(x-y for x,y in zip(a,b))
def scale(a,s):return tuple(x*s for x in a)
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def length(a):return math.sqrt(dot(a,a))
def unit(a):
    size=length(a)
    if size<1e-12:raise ValueError('Cannot normalize a zero-length IK vector')
    return scale(a,1/size)

def solve(root,knee,end,target,pole,source_limits=False):
    """Return knee/end positions preserving segment lengths and pole side.

    source_limits applies Studio_SolveIK's published reach limits. SFM rig
    orientation offsets must be reconciled separately before baking rotations.
    """
    if not all(math.isfinite(v) for p in (root,knee,end,target,pole) for v in p):
        raise ValueError('IK positions must be finite')
    upper=length(sub(knee,root));lower=length(sub(end,knee))
    if min(upper,lower)<1e-10:raise ValueError('IK chain has a zero-length segment')
    delta=sub(target,root);distance=length(delta)
    if distance<1e-12:
        delta=sub(end,root)
        if length(delta)<1e-12:delta=sub(knee,root)
    direction=unit(delta)
    epsilon=(upper+lower)*1e-8
    minimum=abs(upper-lower)+epsilon;maximum=upper+lower
    if source_limits:
        minimum=max(abs(upper-lower)*1.15,min(upper,lower)*.15)
        maximum=(upper+lower)*.9998
        if distance<minimum:
            original=sub(end,root)
            if length(original)>1e-12:direction=unit(original)
    solved_distance=max(minimum,min(maximum,distance))
    def perpendicular(vector):return sub(vector,scale(direction,dot(vector,direction)))
    bend=perpendicular(sub(pole,root))
    if length(bend)<epsilon:bend=perpendicular(sub(knee,root))
    if length(bend)<epsilon:
        axis=min(((1,0,0),(0,1,0),(0,0,1)),key=lambda v:abs(dot(v,direction)))
        bend=perpendicular(axis)
    bend=unit(bend)
    along=(upper*upper-lower*lower+solved_distance*solved_distance)/(2*solved_distance)
    height=math.sqrt(max(0.,upper*upper-along*along))
    solved_knee=add(root,add(scale(direction,along),scale(bend,height)))
    solved_end=add(root,scale(direction,solved_distance))
    return {'knee':solved_knee,'end':solved_end,'bend_direction':bend,'clamped':abs(solved_distance-distance)>epsilon,
            'upper_length':upper,'lower_length':lower}
