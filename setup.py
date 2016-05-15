import os
from setuptools import setup

# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name = "bankandbudget",
    version = "0.0.1",
    author = "Jake Sprouse",
    author_email = "jake@jakesprouse.net",
    description = ("Banking and budgeting command-line tools"),
    license = "BSD",
    keywords = "banking financial",
    url = "http://packages.python.org/bankandbudget",
    packages=['bnb', 'tests'],
    long_description=read('README'),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Topic :: Financial",
        "License :: OSI Approved :: BSD License",
    ],
)
