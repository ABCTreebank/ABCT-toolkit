import sys

if sys.version_info[:2] < (3, 8):
    import importlib_metadata as im
else:
    import importlib.metadata as im
# === END IF ===

import logging

# https://packaging.python.org/guides/single-sourcing-package-version/#single-sourcing-the-package-version
__version__ = im.version("abctk")

logging.basicConfig(
    format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
