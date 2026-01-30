#!/usr/bin/env bash
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
pytest web/tests -v
