# -*- coding: utf-8 -*-

# (git root) % sphinx-build -b rst -a ./sphinx .
# Setuptools integration (python setup.py build_sphinx) is broken for direct writing to README.rst in the root dir (https://github.com/sphinx-doc/sphinx/issues/3883).

import os
import sys
sys.path.insert(0, os.path.abspath('../'))

extensions = ['sphinx.ext.autodoc', 'sphinxcontrib.restbuilder']
autodoc_member_order = 'bysource'

master_doc = 'README'
source_suffix = '.rst.in'
