#!/usr/bin/env python
# -*- codig: utf-8 -*-

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(
    name='blackbird-varnish',
    version='0.1.0',
    description=(
        'get various information about varnish.'
    ),
    author='makocchi',
    author_email='makocchi@gmail.com',
    url='https://github.com/Vagrants/blackbird-varnish',
    data_files=[
        ('/opt/blackbird/plugins', ['varnish.py']),
        ('/etc/blackbird/conf.d', ['varnish.cfg'])
    ],
)
