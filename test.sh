#!/bin/bash

set -eux

mypy safer.py
isort safer.py test
black safer.py test
ruff check --fix safer.py test
coverage run $(which pytest)
coverage html
