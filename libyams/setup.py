# from distutils.core import setup
from setuptools import setup, find_packages

setup(
    name='LibYaMS',
    version='0.1.0-dev4',
    packages=find_packages('libyams'),
    install_requires=[
        'python-telegram-bot==7.0.1',
        'requests==2.18.4',
        'wrapt==1.10.11',
        'PyYAML==3.11',
    ],
    license='my private stuff license :p',
    long_description=open('README.md').read(),
)