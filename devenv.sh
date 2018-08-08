#!/bin/bash
source venv/bin/activate || echo 'Failed to load venv'

# add meshlabserver to PATH
MESHLAB_PATH=/Applications/meshlab.app/Contents/MacOS/
export PATH=$MESHLAB_PATH:$PATH
