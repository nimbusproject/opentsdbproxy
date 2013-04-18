#!/usr/bin/env python

"""
@file setup.py
@see http://peak.telecommunity.com/DevCenter/setuptools
"""

import sys
import os

# Add /usr/local/include to the path for macs, fixes easy_install for several packages (like gevent and pyyaml)
if sys.platform == 'darwin':
    os.environ['C_INCLUDE_PATH'] = '/usr/local/include'

version = "0.1.2"

setupdict = {
    'name': 'opentsdbproxy',
    'version': version,
    'description': 'Experimental proxy to add SSL and ACL to OpenTSDB',
    'license': 'Apache 2.0',
    'author': 'University of Chicago',
    'author_email': 'nimbus@mcs.anl.gov',
    'keywords': ['opentsdb'],
    'classifiers': [
    'Development Status :: 3 - Alpha',
    'Environment :: Console',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: Apache Software License',
    'Operating System :: OS Independent',
    'Programming Language :: Python',
    'Topic :: Scientific/Engineering'],
}

from setuptools import setup, find_packages
setupdict['packages'] = find_packages()

setupdict['test_suite'] = 'opentsdb'

setupdict['install_requires'] = ['gevent>=0.13.7']
setupdict['tests_require'] = ['nose', 'mock']
setupdict['extras_require'] = {
    'test': setupdict['tests_require'],
    'django_authz': ["django >= 1.4, < 1.5", "MySQL-python"]
}
setupdict['test_suite'] = 'nose.collector'

setupdict['entry_points'] = {
    'console_scripts': [
        'opentsdb-proxy=opentsdbproxy.cli:main',
    ]
}

setup(**setupdict)
