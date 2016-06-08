from setuptools import setup, find_packages
import os


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


DESCRIPTION = read('README.rst')
setup(
    name='umap2',
    version='2.0.0a1',
    description='USB Host Security Assessment Tool - Revision 2',
    long_description=DESCRIPTION,
    author='NCCGroup & Cisco SAS team',
    author_email='',
    url='https://github.com/nccgroup/umap2',
    packages=find_packages(),
    install_requires=['docopt', 'kittyfuzzer'],
    keywords='security,usb,fuzzing,kitty',
    entry_points={
        'console_scripts': [
            'umap2detect=umap2.apps.detect_os:main',
            'umap2emulate=umap2.apps.emulate:main',
            'umap2fuzz=umap2.apps.fuzz:main',
            'umap2list=umap2.apps.list_classes:main',
            'umap2scan=umap2.apps.scan:main',
            'umap2stages=umap2.apps.makestages:main',
            'umap2kitty=umap2.fuzz.fuzz_engine:main',
        ]
    },
    package_data={}
)
