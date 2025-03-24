#!/bin/bash
set -e

sleep 5 # wait for selenium to be ready
source /var/local/py_venv/bin/activate
python dg_selenium.py "http://selenium-chrome:4444/wd/hub"