#!/usr/bin/env python3

import os
import shutil
import subprocess
import requests
import sys

from pathlib import Path
from git import Repo
from gzip import GzipFile

def download_file_if_needed(filename: str, url: str) -> None:
    if(os.path.isfile(filename.replace(".gz", ""))):
        return

    print(f"Downloading {url} to {filename}...")
    with requests.get(url) as r:
        with open(filename, "wb") as fout:
            for chunk in r.iter_content(32768):
                fout.write(chunk)

    if filename.endswith("gz"):
        print(f"Extracting {filename}...")
        with GzipFile(filename) as fin:
            with open(filename.replace(".gz", ""), "wb") as fout:
                for chunk in fin:
                    fout.write(chunk)

        os.unlink(filename)


if not Path("cbl").exists():
    print("Cloning couchbase-lite-core repo...")
    Repo.clone_from("https://github.com/couchbase/couchbase-lite-core", "cbl", multi_options=["--branch=staging/master", "--recursive"])

core_repo = Repo("cbl")
core_repo.git.checkout("staging/master")
print("Pulling from staging/master...")
core_repo.remote().pull()
print("Updating submodules...")
core_repo.submodule_update()

sys.path.append(os.path.join(os.getcwd(), "cbl", "tools"))
from fetch_litecore_version import download_litecore, resolve_platform_path, import_platform_extensions ,get_cbl_build
full_path = resolve_platform_path(os.path.join(os.getcwd(), "cbl", "tools"))
import_platform_extensions(full_path)
shutil.rmtree(Path('downloaded'), ignore_errors=True)
Path('downloaded').mkdir()
os.chdir('downloaded')

if sys.platform == "win32":
    download_litecore(["windows-win64"], debug=False, dry=False, build=None, repo=Path('../cbl').resolve(), ee=True, output_path=os.getcwd())

    # TEMPORARY HACK: Flatten directory for Windows artifacts
    shutil.copyfile(Path('windows', 'lib', 'LiteCore.lib'), Path('windows', 'LiteCore.lib'))
    shutil.copyfile(Path('windows', 'bin', 'LiteCore.dll'), Path('windows', 'LiteCore.dll'))
    shutil.copyfile(Path('windows', 'bin', 'LiteCore.pdb'), Path('windows', 'LiteCore.pdb'))
    Path('../build').mkdir(exist_ok=True)
    os.chdir('../build')
    subprocess.run(f'cmake -DBUILD_ENTERPRISE=ON -DLITECORE_PREBUILT_LIB="{Path(os.getcwd()).joinpath("..", "downloaded", "windows", "LiteCore.lib").resolve()}" -A x64 ../cbl', shell=True)
    subprocess.run('cmake --build . --target C4Tests --config MinSizeRel --parallel 8', shell=True)
elif sys.platform == "darwin":
    download_litecore(["macosx"], debug=False, dry=False, build=None, repo=Path('../cbl').resolve(), ee=True, output_path=os.getcwd())
    Path('../build').mkdir(exist_ok=True)
    os.chdir('../build')
    subprocess.run(f'cmake -DCMAKE_BUILD_TYPE=MinSizeRel -DBUILD_ENTERPRISE=ON -DLITECORE_PREBUILT_LIB="{Path(os.getcwd()).joinpath("..", "downloaded", "macos", "lib", "libLiteCore.dylib").resolve()}" ../cbl', shell=True)
    subprocess.run('make -j8 C4Tests', shell=True)
else:
    download_litecore(["linux"], debug=False, dry=False, build=None, repo=Path('../cbl').resolve(), ee=True, output_path=os.getcwd())
    Path('../build').mkdir(exist_ok=True)
    os.chdir('../build')
    subprocess.run(f'cmake -DCMAKE_BUILD_TYPE=MinSizeRel -DBUILD_ENTERPRISE=ON -DLITECORE_PREBUILT_LIB="{Path(os.getcwd()).joinpath("..", "downloaded", "linux", "lib", "libLiteCore.so").resolve()}" ../cbl', shell=True)
    subprocess.run('make -j8 C4Tests', shell=True)

showfast_dir = Path('../showfast').absolute()
shutil.rmtree(showfast_dir, ignore_errors=True)
showfast_dir.mkdir()
os.environ['CBL_SHOWFAST_DIR'] = str(showfast_dir)
os.chdir('C/tests')

download_file_if_needed(str(Path('C/tests/data/geoblocks.json')), 'https://raw.githubusercontent.com/arangodb/example-datasets/master/IPRanges/geoblocks.json')
download_file_if_needed(str(Path('C/tests/data/names_300000.json')), 'https://github.com/arangodb/example-datasets/raw/master/RandomUsers/names_300000.json')
download_file_if_needed(str(Path('C/tests/data/en-wikipedia-articles-1000-1.json.gz')), "https://raw.githubusercontent.com/diegoceccarelli/json-wikipedia/master/src/test/resources/misc/en-wikipedia-articles-1000-1.json.gz")

if sys.platform == "win32":
    os.chdir("MinSizeRel")
    subprocess.run('C4Tests.exe -r list "[Perf]"', shell=True)
    os.chdir("../../../..")
else:   
    subprocess.run('./C4Tests -r list "[Perf]"', shell=True)
    os.chdir("../../..")

with open("version.txt", "w") as fout:
    fout.write(get_cbl_build(Path('cbl').resolve()))
