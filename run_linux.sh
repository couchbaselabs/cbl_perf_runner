#!/bin/bash

pushd `dirname "$0"`

if [ -z $CB_PASSWORD ]; then
    echo "Required environment variable CB_PASSWORD not set!"
    exit 1
fi

if [ -z $CB_SERVER ]; then
    echo "Required environment variable CB_SERVER not set!"
    exit 1
fi

if [ -z $CB_VERSION ]; then
    echo "Required environment variable CB_VERSION not set!"
    exit 1
fi

python3.7 --version > /dev/null
NO_37=$?

if [ $NO_37 ]; then
    PYTHON=python3
else
    PYTHON=python3.7
fi

virtualenv -p $PYTHON venv
source venv/bin/activate
pip install -r requirements.txt

src/cbl_run_litecore_perf.py
src/cbl_upload.py showfast --username cbl_perf --password $CB_PASSWORD --server $CB_SERVER --build $CB_VERSION