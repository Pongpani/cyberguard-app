$ErrorActionPreference = 'Stop'
$taskRoot = $PSScriptRoot
$taskPython = Join-Path $taskRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $taskPython)) { throw 'Create .venv and install backend/requirements.txt first. See README.md.' }
Push-Location (Join-Path $taskRoot 'frontend')
try {
    if (-not (Test-Path -LiteralPath 'node_modules')) {
        & npm.cmd ci
        if ($LASTEXITCODE -ne 0) { throw 'npm ci failed' }
    }
    & npm.cmd run build
    if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed' }
} finally { Pop-Location }
Push-Location (Join-Path $taskRoot 'backend')
try {
    & $taskPython manage.py migrate
    if ($LASTEXITCODE -ne 0) { throw 'Database migration failed' }
    & $taskPython manage.py collectstatic --noinput
    if ($LASTEXITCODE -ne 0) { throw 'Static collection failed' }
    Write-Host 'CyberGuard: http://127.0.0.1:8000  (Ctrl+C to stop)'
    & $taskPython manage.py runserver 127.0.0.1:8000 --noreload
} finally { Pop-Location }

