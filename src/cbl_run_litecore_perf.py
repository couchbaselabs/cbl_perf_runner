#!/usr/bin/env python3

import os
import subprocess
import requests

from pathlib import Path
import sys
from typing import Union
import git
from git import Repo
from alive_progress import alive_bar
from gzip import GzipFile

class CloneProgress(git.RemoteProgress):
    OP_CODES = [
        "BEGIN",
        "CHECKING_OUT",
        "COMPRESSING",
        "COUNTING",
        "END",
        "FINDING_SOURCES",
        "RECEIVING",
        "RESOLVING",
        "WRITING",
    ]
    OP_CODE_MAP = {
        getattr(git.RemoteProgress, _op_code): _op_code for _op_code in OP_CODES
    }

    def __init__(self) -> None:
        super().__init__()
        self.alive_bar_instance = None

    @classmethod
    def get_curr_op(cls, op_code: int) -> str:
        """Get OP name from OP code."""
        # Remove BEGIN- and END-flag and get op name
        op_code_masked = op_code & cls.OP_MASK
        return cls.OP_CODE_MAP.get(op_code_masked, "?").title()

    def update(
        self,
        op_code: int,
        cur_count: Union[str, float],
        max_count: Union[str, float] = None,
        message: Union[str, None] = "",
    ) -> None:
        # Start new bar on each BEGIN-flag
        if op_code & self.BEGIN:
            self.curr_op = self.get_curr_op(op_code)
            self._dispatch_bar(title=self.curr_op)

        self.bar(cur_count / max_count)
        self.bar.text(message)

        # End progress monitoring on each END-flag
        if op_code & git.RemoteProgress.END:
            self._destroy_bar()

    def _dispatch_bar(self, title: Union[str, None] = "") -> None:
        """Create a new progress bar"""
        self.alive_bar_instance = alive_bar(manual=True, title=title)
        self.bar = self.alive_bar_instance.__enter__()

    def _destroy_bar(self) -> None:
        """Destroy an existing progress bar"""
        self.alive_bar_instance.__exit__(None, None, None)

class SubmoduleProgress(git.RootUpdateProgress):
    def update(
        self,
        op_code: int,
        cur_count: Union[str, float],
        max_count: Union[str, float] = None,
        message: Union[str, None] = "",
    ) -> None:
        print(message)

def download_file_if_needed(filename: str, url: str) -> None:
    if(os.path.isfile(filename.replace(".gz", ""))):
        return

    print(f"Downloading {url} to {filename}...")
    with requests.get(url) as r:
        with alive_bar() as bar:
            bar.text("Progress")
            with open(filename, "wb") as fout:
                for chunk in r.iter_content(32768):
                    fout.write(chunk)
                    bar(len(chunk))

    if filename.endswith("gz"):
        print(f"Extracting {filename}...")
        with GzipFile(filename) as fin:
            with open(filename.replace(".gz", ""), "wb") as fout:
                for chunk in fin:
                    fout.write(chunk)

        os.unlink(filename)



if not Path("cbl").exists():
    print("Cloning couchbase-lite-core repo...")
    Repo.clone_from("https://github.com/couchbase/couchbase-lite-core", "cbl", multi_options=["--branch=staging/master"], progress=CloneProgress())

core_repo = Repo("cbl")
core_repo.git.checkout("staging/master")
print("Pulling from staging/master...")
core_repo.remote().pull(progress=CloneProgress())
print("Updating submodules...")
core_repo.submodule_update(progress=SubmoduleProgress())

sys.path.append(os.path.join(os.getcwd(), "cbl", "scripts"))
from fetch_litecore_version import download_litecore, resolve_platform_path, import_platform_extensions ,get_cbl_build
full_path = resolve_platform_path(os.path.join(os.getcwd(), "cbl", "scripts"))
import_platform_extensions(full_path)
Path('downloaded').mkdir(exist_ok=True)
os.chdir('downloaded')

if sys.platform == "win32":
    download_litecore(["windows-win64"], debug=False, dry=False, build=None, repo=Path('../cbl').resolve(), ee=True, output_path=os.getcwd())
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
showfast_dir.unlink(missing_ok=True)
showfast_dir.mkdir()
os.environ['CBL_SHOWFAST_DIR'] = str(showfast_dir)
os.chdir('C/tests')

download_file_if_needed('C/tests/data/geoblocks.json', 'https://raw.githubusercontent.com/arangodb/example-datasets/master/IPRanges/geoblocks.json')
download_file_if_needed('C/tests/data/names_300000.json', 'https://github.com/arangodb/example-datasets/raw/master/RandomUsers/names_300000.json')
download_file_if_needed('C/tests/data/en-wikipedia-articles-1000-1.json.gz', "https://raw.githubusercontent.com/diegoceccarelli/json-wikipedia/master/src/test/resources/misc/en-wikipedia-articles-1000-1.json.gz")

if sys.platform == "win32":
    os.chdir("MinSizeRel")
    subprocess.run('C4Tests.exe -r list "[Perf]"', shell=True)
    os.chdir("../../../..")
else:   
    subprocess.run('./C4Tests -r list "[Perf]"', shell=True)
    os.chdir("../../..")

with open("version.txt", "w") as fout:
    fout.write(get_cbl_build(Path('cbl').resolve()))
