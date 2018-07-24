import sys

py_version = (sys.version_info.major, sys.version_info.minor)
if py_version < (3, 5):
    raise ValueError(
        "This module is only compatible with Python 3.5+, but you are running "
        "Python {}.".format(py_version))

from setuptools import setup

setup(
    name='gpumux',
    packages=['gpumux'],
    version='1.0.0',
    install_requires=[
      "flask",
    ],
    author='David Berthelot, Tom B Brown',
    author_email='dberth@google.com, tomfeelslucky@google.com',
    scripts=[
      'bin/gpumux',
    ]
)
