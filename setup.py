"""
setup.py
"""
from setuptools import setup

setup(
    name='metareader',
    packages=['metareader'],
    version='1.0',
    description='Compact utility for parsing data from Valossa Core metadata.',
    author='Olli Puhakka',
    author_email='olli.puhakka@valossa.com',
    url='https://github.com/valossalabs/metadata-reader',
    # download_url = 'https://github.com/valossalabs/metadata-reader/archive/0.1.tar.gz',
    keywords=['valossa', 'metadata'],
    # classifiers = [],
    extras_require={
        'plot': ['matplotlib'],
    },
    # py_modules = ['reader','metareader'],
    # long_description = open('README.md').read(),
)
