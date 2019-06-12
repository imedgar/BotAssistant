#!/bin/sh
cd "$(dirname "$0")";
CWD="$(pwd)"
echo $CWD
python web-api.py
