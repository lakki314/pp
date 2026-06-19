<#
Build offline Python vendor modules on a Windows machine with pip.

Purpose:
  Downloads Python 3.11 Linux x86_64 compatible wheels and extracts them into:
    vendor\site-packages

Use this when the target Linux server does not have pip access.

Run from PowerShell:
  powershell -ExecutionPolicy Bypass -File .\build_offline_vendor_windows.ps1

This script uses the command named "python" by default.
If Python is not in PATH, pass the full path:
  powershell -ExecutionPolicy Bypass -File .\build_offline_vendor_windows.ps1 -PythonExe "C:\Path\To\python.exe"

Output:
  offline_vendor_py311_linux_x86_64.zip
#>

param(
    [string]$PythonExe = "python",
    [string]$PythonVersion = "3.11",
    [string]$PythonAbi = "cp311",
    [string]$Platform = "manylinux2014_x86_64",
    [string]$OutputZip = "offline_vendor_py311_linux_x86_64.zip"
)

$ErrorActionPreference = "Stop"

function Test-PythonCommand {
    param([string]$Exe)

    if ($Exe -match "[\\/]") {
        if (-not (Test-Path $Exe)) {
            throw "Python executable was not found: $Exe"
        }
    } else {
        $cmd = Get-Command $Exe -ErrorAction SilentlyContinue
        if (-not $cmd) {
            throw "Python command '$Exe' was not found. Run 'python --version' to verify Python is in PATH, or rerun with -PythonExe 'C:\Path\To\python.exe'."
        }
    }

    $version = & $Exe --version 2>&1
    if ($LASTEXITCODE -ne 0 -or "$version" -notmatch "Python") {
        throw "The command '$Exe' did not run as Python. Output: $version"
    }

    Write-Host "Using Python command: $Exe"
    Write-Host "$version"
}

function Invoke-Python {
    param([string[]]$ArgsList)

    & $PythonExe @ArgsList
    if ($LASTEXITCODE -ne 0) {
        throw "Python command failed: $PythonExe $($ArgsList -join ' ')"
    }
}

Test-PythonCommand -Exe $PythonExe

$Root = Get-Location
$Wheelhouse = Join-Path $Root "wheelhouse"
$VendorRoot = Join-Path $Root "vendor"
$VendorSitePackages = Join-Path $VendorRoot "site-packages"
$Requirements = Join-Path $Root "requirements-offline.txt"
$ExtractScript = Join-Path $Root "extract_wheels.py"

Write-Host "Preparing offline vendor build in $Root"

@"
Flask==3.0.3
requests==2.32.3
python-dotenv==1.0.1
ldap3==2.9.1
openpyxl==3.1.5
gunicorn==22.0.0
"@ | Set-Content -Path $Requirements -Encoding ASCII

if (Test-Path $Wheelhouse) { Remove-Item -Recurse -Force $Wheelhouse }
if (Test-Path $VendorRoot) { Remove-Item -Recurse -Force $VendorRoot }
if (Test-Path $OutputZip) { Remove-Item -Force $OutputZip }

New-Item -ItemType Directory -Force -Path $Wheelhouse | Out-Null
New-Item -ItemType Directory -Force -Path $VendorSitePackages | Out-Null

Write-Host "Downloading wheels for Python $PythonVersion, ABI $PythonAbi, platform $Platform ..."

Invoke-Python @(
    "-m", "pip", "download",
    "--dest", $Wheelhouse,
    "--only-binary=:all:",
    "--python-version", $PythonVersion,
    "--implementation", "cp",
    "--abi", $PythonAbi,
    "--platform", $Platform,
    "-r", $Requirements
)

Write-Host "Extracting wheels into $VendorSitePackages ..."

@"
import pathlib
import shutil
import zipfile

wheelhouse = pathlib.Path(r"$Wheelhouse")
target = pathlib.Path(r"$VendorSitePackages")

if target.exists():
    shutil.rmtree(target)
target.mkdir(parents=True, exist_ok=True)

wheels = sorted(wheelhouse.glob("*.whl"))
if not wheels:
    raise SystemExit("No wheels found in wheelhouse")

for wheel in wheels:
    print(f"Extracting {wheel.name}")
    with zipfile.ZipFile(wheel) as zf:
        zf.extractall(target)

for pycache in target.rglob("__pycache__"):
    shutil.rmtree(pycache, ignore_errors=True)
for pyc in target.rglob("*.pyc"):
    try:
        pyc.unlink()
    except FileNotFoundError:
        pass

print(f"Extracted {len(wheels)} wheels into {target}")
"@ | Set-Content -Path $ExtractScript -Encoding UTF8

Invoke-Python @($ExtractScript)

Write-Host "Creating zip $OutputZip ..."
Compress-Archive -Path $VendorRoot -DestinationPath $OutputZip -Force

Write-Host "Done. Output file: $OutputZip"
Write-Host "Copy the vendor folder from this zip into your application folder on the Linux server:"
Write-Host "  /opt/middleware-jvm-restart/app/vendor/site-packages"
