""" set files for distrubution """
import uuid
from setuptools import setup
from pip.req import parse_requirements

# parse_requirements() returns generator of pip.req.InstallRequirement objects
install_reqs = parse_requirements('requirements.txt', session=uuid.uuid1())

# reqs is a list of requirement
# e.g. ['django==1.5.1', 'mezzanine==1.4.6']
reqs = [str(ir.req) for ir in install_reqs]

setup(
    # Application name:
    name="pypayd-ng",

    # Version number (initial):
    version="0.0.2",

    # Application author details:
    author="Serge Victor",
    author_email="pyhon@random.re",

    # Packages
    packages=["pypayd-ng"],

    # Main script is only one
    scripts=["pypayd-ng/pypayd-ng.py"],

    # Include additional files into the package
    include_package_data=True,

    # Details
    url="https://github.com/ser/pypayd-ng/",

    # PyPi description
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Environment :: Console",
        "Framework :: CherryPy",
        "Framework :: Flask",
        "Topic :: Office/Business :: Financial",
    ],
    license="MIT",
    description="A small daemon for processing bitcoin payments compatible with modern HD wallets",
    long_description=open("README.rst").read(),

    # Dependent packages (distributions)
    install_requires=reqs
)
