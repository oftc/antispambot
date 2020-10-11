#!/usr/bin/env bash

FILES_W_PYTEST_UNIT_TESTS=( tmb_util/wordwrap.py tmb_util/lcsv.py )

pytest -vv "${FILES_W_PYTEST_UNIT_TESTS[@]}"
