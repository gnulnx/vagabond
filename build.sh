#!/usr/bin/env bash
rm -rf dist/
python setup.py sdist
python setup.py bdist_wheel
pip install  dist/vagabond-0.0.1.tar.gz 
