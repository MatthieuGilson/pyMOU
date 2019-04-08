"""setup.py"""

from setuptools import setup, find_packages


with open("requirements.txt") as reqs_file:
    REQS = [line.rstrip() for line in reqs_file.readlines() if line[0] not in ['\n', '-', '#']]

config = {
    'name': 'pyMOU',
    'description': ('A library for connectivity estimation and analysis in Python / NumPy.'),
    # Check these exist in PyPI
    'keywords': 'network dynamics, connectivity estimation',
    'classifiers': [
        'Development Status :: 1 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'Intended Audience :: Education',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Topic :: Scientific/Engineering :: Bio-Informatics',
        'Topic :: Scientific/Engineering :: Information Analysis',
        'Topic :: Scientific/Engineering :: Mathematics',
        'Topic :: Scientific/Engineering :: Physics',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
    'author': 'Andrea Insabato, Gorka Zamora-López, Matthieu Gilson',
    'author_email': '',
    'url': 'https://github.com/MatthieuGilson/pyMOU',
    'version': '0.0.12',
    'install_requires': REQS,
    'packages': find_packages(exclude=['doc', '*tests*']),
    'scripts': [],
    'include_package_data': True
    }

setup(**config)
