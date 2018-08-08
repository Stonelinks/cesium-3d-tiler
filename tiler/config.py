import os
import sys

ROOT_PATH = os.path.dirname(os.path.realpath(__file__))

DATA_PATH = os.path.join(ROOT_PATH, '..', 'data')

NUM_LAYERS = 5
NUM_THREADS = 6

"""
Quality threshold for penalizing bad shaped faces.
The value is in the range [0..1]0 accept any kind of face (no
penalties), 0.5 penalize faces with quality less than 0.5,
proportionally to their shape.
"""
SIMPLIFICATION_MESH_QUALITY = 0.07

"""
Keep these high to preserve edges and texture mapping
"""
SIMPLIFICATION_EDGE_WEIGHT = 100.0
SIMPLIFICATION_TEXTURE_WEIGHT = 100.0


"""
Minimum bound of points to keep on lowest quality zoom layer (the big tiles)
The value is in the range [0..1]
"""
SIMPLIFICATION_MIN = 0.1

"""
Maximum bound of points to keep on highest quality zoom layer (the small tiles)
The value is in the range [0..1]
"""
SIMPLIFICATION_MAX = 0.8
