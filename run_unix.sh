#!/bin/bash -xe

pushd `dirname "$0"`

do_upload=1
if [ -z $SHOWFAST_SERVER ]; then
   echo "Required environment variable CB_SERVER not set, upload will be skipped!"
   do_upload=0
fi

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

python src/cbl_run_litecore_perf.py

if [ $do_upload == 1 ]; then
    cb_version=`cat version.txt`
    python src/cbl_upload.py showfast --server $SHOWFAST_SERVER --build $cb_version
fi

