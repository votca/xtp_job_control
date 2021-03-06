#!/usr/bin/env python
from setuptools import (find_packages, setup)
import os

HERE = os.path.abspath(os.path.dirname(__file__))
version = {}
with open(os.path.join(HERE, 'xtp_job_control', '__version__.py')) as f:
    exec(f.read(), version)


def readme():
    with open('README.md') as f:
        return f.read()


setup(
    name='xtp_job_control',
    version=version['__version__'],
    description='Workflow engine to use the VOTCA-XTP library',
    license='Apache-2.0',
    url='https://github.com/votca/xtp_job_control',
    author=['Felipe Zapata'],
    author_email='fzapata@esciencecenter.nl',
    keywords='chemistry materials',
    long_description=readme(),
    long_description_content_type='text/markdown',
    packages=find_packages(),
    classifiers=[
        'License :: OSI Approved :: Apache Software License',
        'Intended Audience :: Science/Research',
        'Programming Language :: Python :: 3.7',
        'Development Status :: 4 - Beta',
        'Topic :: Scientific/Engineering :: Chemistry'
    ],
    install_requires=[
        'noodles[numpy]', 'pyyaml==5.1', 'schema'],
    tests_require=[
        'pytest',
        'pytest-cov',
        'pycodestyle',
    ],
    extras_require={
        'test': ['pytest>=4.1.0', 'pytest-cov>=2.6.1', 'coverage',
                 'codacy-coverage']},
    entry_points={
        'console_scripts': [
            'run_xtp_workflow=xtp_job_control.workflows.run_workflow:main',
        ]
    }
)
