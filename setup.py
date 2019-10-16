#!/usr/bin/env python
"""
setup.py
"""
from setuptools import setup

setup(
    name='metareader',
    packages=['metareader', "metareader.lib"],
    version='1.0-beta.1',
    install_requires=[],  # ['argcomplete'], TODO: autocompletion
    description='Compact utility for parsing data from Valossa Core metadata.',
    author='Olli Puhakka',
    author_email='olli.puhakka@valossa.com',
    url='https://github.com/valossalabs/metadata-reader',
    data_files=[
        ('metareader', ['blacklist.json']),
    ],
    extras_require={
        'plot': ['matplotlib'],
    },
)
