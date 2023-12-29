#!/bin/bash

set -eux

mypy safer
isort safer test
black safer test
ruff check --fix safer test
coverage run $(which pytest)
coverage html
