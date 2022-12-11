#! /bin/bash

set -e

. activate.sh
flake8 personalmonitor_collector tests
pylint personalmonitor_collector tests
mypy personalmonitor_collector tests