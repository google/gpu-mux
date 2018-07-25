from setuptools import setup

setup(
    name='gpumux',
    version='1.0.0',
    description='A simple web interface for queueing GPU jobs in the cloud.',
    author='David Berthelot',
    author_email='dberth@google.com',
    url='https://github.com/google/gpu-mux',
    packages=['gpumux'],
    classifiers=[
      'Development Status :: 5 - Production/Stable',
      'Framework :: Flask',
      'Intended Audience :: Developers',
      'License :: OSI Approved :: Apache Software License',
      'Programming Language :: Python',
      'Programming Language :: Python :: 3',
      'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
      'Topic :: Scientific/Engineering',
    ],
    install_requires=['flask'],
    entry_points={
      'console_scripts': ['gpumux=gpumux.gpumux:main']
    },
    include_package_data=True,
    package_data={
      'gpumux': ['templates/*.html']
    },
)
