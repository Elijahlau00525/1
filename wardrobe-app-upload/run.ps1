param(
  [switch]$Init
)

$ErrorActionPreference = "Stop"

if ($Init) {
  python -m venv .venv
  .\.venv\Scripts\python.exe -m pip install --upgrade pip
  .\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt

  if (!(Test-Path backend\.env) -and (Test-Path backend\.env.example)) {
    Copy-Item backend\.env.example backend\.env
    Write-Host "Created backend/.env from template"
  }
}

.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --app-dir backend --host 0.0.0.0 --port 8000
