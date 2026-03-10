import sys
import os

# ensure src/ is on the import path for the package
root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(root, 'src'))
