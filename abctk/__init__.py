import importlib.metadata as im
import logging

# https://packaging.python.org/guides/single-sourcing-package-version/#single-sourcing-the-package-version

__version__ = im.version("abctk")

logging.basicConfig(
    format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
