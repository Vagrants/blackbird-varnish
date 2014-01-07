#!/usr/bin/env python
# -*- codig: utf-8 -*-

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(
    name='blackbird-varnish',
    version='0.0.1',
    description=(
        'get various information about varnish.'
    ),
    author='hoge',
    author_email='hoge@example.com',
    url='https://github.com/Vagrants/blackbird-varnish',
)
