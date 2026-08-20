import sys
import os

backend_dir = os.path.join(os.path.dirname(__file__), "..", "..", "backend")
root_dir = os.path.join(os.path.dirname(__file__), "..", "..")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
