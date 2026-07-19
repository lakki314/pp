[CmdletBinding()]
param(
    [string]$PythonCommand = "py -3.11",
    [string]$ProjectRoot = ""
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($ProjectRoot)) {
    $ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}

$VendorDir = Join-Path $ProjectRoot "vendor"
$LockFile = Join-Path $ProjectRoot "requirements.lock.txt"

if (-not (Test-Path $LockFile)) {
    throw "requirements.lock.txt was not found at $LockFile"
}

$pythonParts = $PythonCommand -split " "
$pythonExe = $pythonParts[0]
$pythonArgs = @()
if ($pythonParts.Length -gt 1) {
    $pythonArgs = $pythonParts[1..($pythonParts.Length - 1)]
}

function Invoke-Python {
    param([string[]]$Arguments)
    & $pythonExe @pythonArgs @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Python command failed: $pythonExe $($pythonArgs -join ' ') $($Arguments -join ' ')"
    }
}

if (Test-Path $VendorDir) {
    Remove-Item -Recurse -Force $VendorDir
}
New-Item -ItemType Directory -Path $VendorDir | Out-Null

$purePythonPackages = @(
    "blinker==1.9.0",
    "click==8.1.8",
    "Flask==3.1.3",
    "Flask-WTF==1.2.2",
    "gunicorn==23.0.0",
    "itsdangerous==2.2.0",
    "Jinja2==3.1.6",
    "ldap3==2.9.1",
    "packaging==25.0",
    "pyasn1==0.6.1",
    "python-dotenv==1.2.1",
    "Werkzeug==3.1.3",
    "WTForms==3.2.1",
    "XlsxWriter==3.2.9"
)

Invoke-Python -Arguments @(
    "-m", "pip", "download", "--no-deps", "--only-binary=:all:",
    "--platform", "any", "--implementation", "py", "--python-version", "3.9",
    "--dest", $VendorDir
) + $purePythonPackages

# MarkupSafe publishes compiled wheels for common operating systems but not AIX.
# Download its source archive so it can create a plain-Python build on AIX.
Invoke-Python -Arguments @(
    "-m", "pip", "download", "--no-deps", "--no-binary=:all:",
    "--dest", $VendorDir, "MarkupSafe==3.0.3"
)

# Bundled bootstrap/build tools. These are platform-neutral wheels.
Invoke-Python -Arguments @(
    "-m", "pip", "download", "--no-deps", "--only-binary=:all:",
    "--dest", $VendorDir,
    "pip==25.3", "setuptools==80.9.0", "wheel==0.45.1"
)

$hashFile = Join-Path $VendorDir "SHA256SUMS"
Get-ChildItem -Path $VendorDir -File |
    Where-Object { $_.Name -ne "SHA256SUMS" } |
    Sort-Object Name |
    ForEach-Object {
        $hash = (Get-FileHash -Algorithm SHA256 -Path $_.FullName).Hash.ToLowerInvariant()
        "$hash  $($_.Name)"
    } | Set-Content -Encoding ascii $hashFile

Write-Host "AIX vendor bundle created at: $VendorDir"
Write-Host "Files: $((Get-ChildItem -Path $VendorDir -File).Count)"
Write-Host "Copy the complete project directory to AIX, then run scripts/install_offline_aix.sh."
