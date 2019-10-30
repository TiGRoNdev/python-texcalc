# -*- coding: utf-8 -*-
# =================================================================
#
# Authors: Igor Nazarov <igoryan.ms@gmail.com>
#
# Copyright (c) 2019 Igor Nazarov
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
# =================================================================

from setuptools import setup, find_packages

import sys
import os

if sys.version_info < (3, 5):
    sys.exit('Sorry, Python < 3.5 is not supported')


def read(filename, encoding="utf-8"):
    full_path = os.path.join(os.path.dirname(__file__), filename)
    with open(full_path, encoding=encoding) as fh:
        contents = fh.read().strip()
    return contents


setup(
    name='texcalc',
    description="Math calculations on LaTeX strings in pure Python.",
    long_description=read("README.md"),
    license='MIT',
    version=read("VERSION.txt"),
    platforms='all',
    packages=find_packages(),
    author='Igor Nazarov',
    author_email='igoryan.ms@gmail.com',
    maintainer='Igor Nazarov',
    maintainer_email='igoryan.ms@gmail.com',
    url='https://github.com/TiGRoNdev/texcalc',
)
