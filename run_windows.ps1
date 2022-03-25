Push-Location $PSScriptRoot
$do_upload = $true

if(-Not $env:SHOWFAST_SERVER) {
    Write-Warning "Required environment variable CB_SERVER not set, upload will be skipped!"
    $do_upload = $false
}

python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt

python src/cbl_run_litecore_perf.py

if($do_upload) {
    $cb_version=$(Get-Content version.txt)
    python src/cbl_upload.py showfast --server $env:SHOWFAST_SERVER --build $cb_version
}

deactivate
Pop-Location