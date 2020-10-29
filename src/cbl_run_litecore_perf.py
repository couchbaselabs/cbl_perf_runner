#!/usr/bin/env python3

import requests
import json
import tarfile
import os
import subprocess
import shutil

from pathlib import Path
from packaging import version
from sys import platform

r = requests.get('http://mobile.jenkins.couchbase.com/view/Couchbase_Lite_Core/job/couchbase-lite-core-edition-build/api/json?tree=builds[building,result,actions[parameters[name,value]]]')
result = json.loads(r.text)
min_version = version.parse('3.0.0')

for child in result['builds']:
    actions = next(x for x in child['actions'] if x['_class'] == 'hudson.model.ParametersAction')
    parameters = actions['parameters']
    if child['result'] != 'SUCCESS' or child['building']:
        continue

    edition = next(p['value'] for p in parameters if p['name'] == 'EDITION')
    if edition != 'enterprise':
        continue

    release_version = next(version.parse(p['value']) for p in parameters if p['name'] == 'RELEASE')
    if(release_version < min_version):
        continue

    bld_num = next(p['value'] for p in parameters if p['name'] == 'BLD_NUM')
    print('Found latest stable build as {}-{}'.format(release_version, bld_num))
    with open('version.txt', 'w') as fout:
        fout.write('{}-{}'.format(release_version, bld_num))
    
    break

# Internal server, this script must be run inside the company network
tarball_url = 'http://latestbuilds.service.couchbase.com/builds/latestbuilds/couchbase-lite-core/{0}/{1}/couchbase-lite-core-{0}-{1}-source.tar.gz'.format(release_version, bld_num)

Path('cbl_src').mkdir(exist_ok=True)
r = requests.get(tarball_url, stream=True)
download_size = int(r.headers['content-length'])
with open('cbl_src/src.tar.gz', 'wb') as fout:
    for chunk in r.iter_content(chunk_size=16384):
        fout.write(chunk)
        print('{} of {} downloaded ({}%)...'.format(fout.tell(), download_size, round(fout.tell() / download_size * 100, 2)), end='\r')

print("\nDownload complete, extracting...")
with tarfile.open('cbl_src/src.tar.gz') as fin:
    fin.extractall(path="cbl_src")

os.remove('cbl_src/src.tar.gz')

Path('build').mkdir(exist_ok=True)
os.chdir('build')

if platform == "linux" or platform == "linux2":
    os.environ['CC'] = 'gcc-7'
    os.environ['CXX'] = 'g++-7'

subprocess.run('cmake -DCMAKE_BUILD_TYPE=MinSizeRel -DBUILD_ENTERPRISE=ON ../cbl_src', shell=True)
subprocess.run('make -j8 C4Tests', shell=True)

showfast_dir = Path('../showfast').absolute()
showfast_dir.mkdir(exist_ok=True)
os.environ['CBL_SHOWFAST_DIR'] = str(showfast_dir)
os.chdir('couchbase-lite-core/C/tests')

for data_file in ['geoblocks.json', 'en-wikipedia-articles-1000-1.json', 'names_300000.json']:
    if not os.path.isfile('C/tests/data/{}'.format(data_file)):
        path = os.path.join(os.environ['HOME'], 'test_data', data_file)
        shutil.copyfile(path, 'C/tests/data/{}'.format(data_file))

subprocess.run('./C4Tests -r list "[Perf]"', shell=True)
