#!/usr/bin/env python2
# Copyright (c) 2010 Joshua Harlan Lifton.
# See LICENSE.txt for details.

from plover import __version__
from plover import __description__
from plover import __long_description__
from plover import __url__
from plover import __download_url__
from plover import __license__

import os
import setuptools
import subprocess

setuptools.setup(
    name = 'plover',
    version = __version__,
    description = __description__,
    long_description = __long_description__,
    url = __url__,
    download_url = __download_url__,
    license = __license__,
    author = 'Joshua Harlan Lifton',
    author_email = 'joshua.harlan.lifton@gmail.com',
    maintainer = 'Joshua Harlan Lifton',
    maintainer_email = 'joshua.harlan.lifton@gmail.com',
    zip_safe = False,
    install_requires = [
        'setuptools',
        'pyserial>=2.7',
        'python-xlib>=0.14',
        'appdirs>=1.4.0',
        'wxPython>=2.8'
    ],
    entry_points = {
        'console_scripts' : [ 'plover = plover.main:main' ],
    },
    packages = [
        'plover', 'plover.machine', 'plover.gui',
        'plover.oslayer', 'plover.dictionary',
    ],
    package_data = {
        'plover' : ['assets/*'],
    },
    data_files = [
        ('share/applications', ['application/Plover.desktop']),
        ('share/pixmaps', ['plover/assets/plover_on.png']),
    ],
    platforms = [
        'Operating System :: POSIX :: Linux',
        'Operating System :: Microsoft :: Windows',
    ],
    classifiers = [
        'Programming Language :: Python',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Development Status :: 4 - Beta',
        'Environment :: X11 Applications',
        'Intended Audience :: End Users/Desktop',
        'Natural Language :: English',
        'Operating System :: POSIX :: Linux',
        'Topic :: Adaptive Technologies',
        'Topic :: Desktop Environment',
    ],
)
