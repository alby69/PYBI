"""Backend package for PyBI."""

import sys
import pybi

# Ensure backend submodules are accessible via backend namespace
sys.modules["backend"] = sys.modules[__name__]
