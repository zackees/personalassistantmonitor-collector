#! /bin/bash

set -e

. activate.sh
echo Running flake8
flake8 personalmonitor_collector tests

echo Running pylint
pylint personalmonitor_collector tests

echo Running mypy
mypy personalmonitor_collector tests