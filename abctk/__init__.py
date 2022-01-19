from packaging.version import Version
import sys
if sys.version_info[:2] < (3, 8):
    import importlib_metadata as im
else:
    import importlib.metadata as im
# === END IF ===

import logging

# https://packaging.python.org/guides/single-sourcing-package-version/#single-sourcing-the-package-version

_version_raw = im.version("abctk")
try:
    __version__ = Version(_version_raw)
except:
    __version__ = _version_raw
    
logging.basicConfig(
    format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

class ABCTException(Exception):
    pass