"""Explicit label-blind query API, retaining the trained batch-conditioned model.

The optional candidate_order reproduces an existing predict_table call exactly.
Default batches sort unique Q by geometry hash, include all S, and use 32 Q.
Only bit-identical coordinates restore support labels; DBU normalization belongs
at the physical interface, not in an undocumented nearest-neighbour match.
"""
import hashlib
import numpy as np
from .score import predict_table, load_members
from .basis import CLASSICAL


def query_table(S_coordinates,S_values,Q_coordinates,context,candidate_order=None):
    s,v,q=map(lambda x:np.asarray(x,float),(S_coordinates,S_values,Q_coordinates))
    if s.ndim!=2 or q.ndim!=2 or v.ndim!=2 or len(s)!=len(v) or s.shape[1]!=q.shape[1] or not len(s):
        raise ValueError('incompatible S/Q shapes')
    if not all(np.isfinite(x).all() for x in (s,v,q)):raise ValueError('nonfinite input')
    if 'labels' in context:raise ValueError('context must contain no query labels')
    sv={}
    for x,y in zip(s,v):
        k=tuple(x)
        if k in sv and not np.array_equal(sv[k],y):raise ValueError('conflicting support')
        sv[k]=y
    points=list(dict.fromkeys(map(tuple,np.vstack([s,q])))) if candidate_order is None else list(map(tuple,np.asarray(candidate_order,float)))
    if len(points)!=len(set(points)) or set(points)!=set(map(tuple,np.vstack([s,q]))):raise ValueError('candidate order must contain exactly the S/Q union')
    idx={x:i for i,x in enumerate(points)}
    observed=np.array([idx[x] for x in sv]); values=np.array(list(sv.values()))
    table=dict(context,coordinates=[list(x) for x in points]);table.pop('labels',None)
    return table,observed,values,np.array([idx[tuple(x)] for x in q])


def predict_queries(S_coordinates,S_values,Q_coordinates,context,checkpoint,query_policy=None):
    """checkpoint is paths or a preloaded (members, scales) pair. No Q labels."""
    policy=query_policy or {};q=np.asarray(Q_coordinates,float)
    members,scales=checkpoint if isinstance(checkpoint,tuple) else load_members(checkpoint)
    basis=tuple(policy.get('basis',CLASSICAL))
    if 'candidate_order' in policy:
        t,o,v,qi=query_table(S_coordinates,S_values,q,context,policy['candidate_order'])
        return predict_table(members,scales,t,o,v,basis)[0][qi]
    hashes=policy.get('query_hashes')
    if hashes is None:hashes=[hashlib.sha256(x.tobytes()).hexdigest() for x in q]
    if len(hashes)!=len(q):raise ValueError('one query hash required per Q')
    order=sorted(range(len(q)),key=lambda i:hashes[i])
    size=policy.get('batch_size',32)
    if size<1:raise ValueError('positive batch size required')
    out=np.empty((len(q),np.asarray(S_values).shape[1]))
    for start in range(0,len(order),size):
        ids=order[start:start+size];t,o,v,qi=query_table(S_coordinates,S_values,q[ids],context)
        out[ids]=predict_table(members,scales,t,o,v,basis)[0][qi]
    return out
