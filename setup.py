import sys

py_version = (sys.version_info.major, sys.version_info.minor)
if py_version < (3, 6):
  raise ValueError(
    "This module is only compatible with Python 3.6+, but you are running "
    "Python {}. We recommend installing conda and adding it to your PATH:"
    "https://conda.io/docs/user-guide/install/index.html".format(py_version))

from setuptools import setup
import berg

setup(
  name='gpumux',
  packages=['gpumux'],
  version='0.0.1',
  install_requires=[
    "flask",
  ],
  author='Tom B Brown',
  author_email='tombrown@google.com',
  extras_require={
    "test": [
      'pytest ~= 3.2',
    ]
  },
  scripts=[
    'bin/gpumux',
  ]
)
