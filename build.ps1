# OpenGSM-Toolkit :: build — gera o OpenGSM-Toolkit.exe (app nativo, onefile, sem console).
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$PY = Resolve-Path "pyenv\Scripts\python.exe"

# fecha instâncias abertas (senão o PyInstaller não sobrescreve o .exe)
Get-Process OpenGSM-Toolkit -ErrorAction SilentlyContinue | Stop-Process -Force

& $PY -m PyInstaller --onefile --windowed --name OpenGSM-Toolkit `
  --collect-all webview `
  --hidden-import server --hidden-import backends --hidden-import tutorials --hidden-import drivers `
  --noconfirm --clean `
  --distpath "." --workpath "tools\_build" --specpath "tools\_build" `
  app.py

Remove-Item -Recurse -Force tools\_build -ErrorAction SilentlyContinue
Write-Host "`nOpenGSM-Toolkit.exe gerado na pasta." -ForegroundColor Green
