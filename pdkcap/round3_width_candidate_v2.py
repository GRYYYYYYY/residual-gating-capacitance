"""Unselected geometry-only dispatch candidate; no frozen deployment changes."""
import numpy as np
from .round3_support import width_linear
from .round3_width_candidate import width_linear_grouped

def width_linear_adaptive(x,values,query):
    support=np.asarray(x,float)
    # Preserve original validation for malformed, empty, or single-width inputs.
    if support.ndim!=2 or not len(support) or not support.shape[1] or np.all(support[:,0]==support[0,0]):
        return width_linear(x,values,query)
    return width_linear_grouped(x,values,query)
