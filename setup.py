
from setuptools import (find_packages, setup)


def readme():
    with open('README.md') as f:
        return f.read()


setup(
    name='xtp_job_control',
    version='0.0.1',
    description='',
    license='Apache-2.0',
    url='https://github.com/votca/xtp_job_control',
    author=['Felipe Zapata'],
    author_email='fzapata_esciencecenter.nl',
    keywords='chemistry materials',
    long_description=readme(),
    packages=find_packages(),
    classifiers=[
        'License :: OSI Approved :: Apache-2.0 License',
        'Intended Audience :: Science/Research',
        'programming language :: python :: 3.5',
        'development status :: 4 - Beta',
        'intended audience :: science/research',
        'topic :: scientific/engineering :: chemistry'
    ],
    install_requires=['noodles'],
    extras_require={
        'test': ['coverage', 'pytest', 'pytest-cov']},
    include_package_data=True,
    package_data={
        'xtp_job_control': ['data/*']
    },
    scripts=[
        'scripts/run_xtp_workflow.py']
)
