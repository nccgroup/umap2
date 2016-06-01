from setuptools import setup, find_packages
import os
import sys


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


VERSION = '2.0.0a'
AUTHOR = 'NCCGroup & Cisco SAS team'
EMAIL = ''
URL = 'https://github.com/BinyaminSharet/umap2'
DESCRIPTION = read('README.rst')
KEYWORDS = 'security,usb,fuzzing,kitty'

setup(
    name='umap2',
    version=VERSION,
    description='USB Host Security Assessment Tool',
    long_description=DESCRIPTION,
    author=AUTHOR,
    author_email=EMAIL,
    url=URL,
    packages=find_packages(),
    install_requires=['docopt'],
    keywords=KEYWORDS,
    entry_points={
        'console_scripts': [
        ]
    },
    package_data={}
)
