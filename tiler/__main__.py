import os
import sys

TILER_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TILER_DIR)

from tiler.tiler import run_tiler

if __name__ == '__main__':
    run_tiler()