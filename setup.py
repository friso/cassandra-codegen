"""Setuptools based setup script for the cassandra-codegen package."""

from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'DESCRIPTION.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='cassandra-codegen',
    version='0.1.0',
    description='Code generator for Cassandra DDL (CQL) and immutable POJO classes (Java) based on YAML descriptions of tables.',
    long_description=long_description,
    url='https://github.com/friso/cassandra-codegen',
    author='Friso van Vollenhoven',
    author_email='f.van.vollenhoven@gmail.com',
    license='Apache Software License',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development :: Code Generators',
    ],

    keywords='cassandra CQL',
    packages=[
        'ccgen',
        'ccgen.cql',
        'ccgen.java',
        'ccgen.generator'
        # 'ccgen.xxx',
    ],
    install_requires=[
        'PyYAML',
        'Jinja2',
    ],
    extras_require={
        'dev': [],
        'test': [],
    },
    package_data={
        # 'sample': ['package_data.dat'],
    },
    data_files=[],
    entry_points={
        'console_scripts': [
            'ccgen=ccgen.ccgen:_main',
        ]
    }
)
