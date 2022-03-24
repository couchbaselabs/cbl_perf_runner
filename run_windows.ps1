python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt

$do_upload = $true
if(-Not $env:CB_PASSWORD) {
    Write-Warning "Required environment variable CB_PASSWORD not set, upload will be skipped!"
    $do_upload = $false
}

if(-Not $env:CB_SERVER) {
    Write-Warning "Required environment variable CB_SERVER not set, upload will be skipped!"
    $do_upload = $false
}

python src/cbl_run_litecore_perf.py

if($do_upload) {
    $cb_version=$(Get-Content version.txt)
    python src/cbl_upload.py showfast --username cbl_perf --password $env:CB_PASSWORD --server $env:CB_SERVER --build $cb_version
}

deactivate