import os
import sys

# Ensure the repository root is importable so `import app...` works when
# pytest is invoked from anywhere.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
