import os
import sys

# Ensure both 'model.schema' and 'pybi.model.schema' are importable in test suites
pybi_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../pybi"))
if pybi_dir not in sys.path:
    sys.path.insert(0, pybi_dir)
