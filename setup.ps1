# OpenGSM Toolkit :: setup — monta o ambiente isolado dentro da pasta.
# Requer Python 3 e Git no PATH. Não instala nada no sistema.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "== 1/5  criando ambiente Python (pyenv/) ==" -ForegroundColor Cyan
if (-not (Test-Path "pyenv\Scripts\python.exe")) { py -3 -m venv pyenv }
$PY = Resolve-Path "pyenv\Scripts\python.exe"
& $PY -m pip install --upgrade pip -q

Write-Host "== 2/5  instalando mtkclient + pywebview + pyinstaller ==" -ForegroundColor Cyan
& $PY -m pip install "git+https://github.com/bkerler/mtkclient.git" pywebview pyinstaller -q

Write-Host "== 3/5  clonando edl + dependências (sem pylzma) ==" -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path tools | Out-Null
if (-not (Test-Path "tools\edl\edl.py")) { git clone --depth 1 https://github.com/bkerler/edl.git tools\edl }
if (Test-Path "tools\edl\requirements.txt") {
    (Get-Content tools\edl\requirements.txt) | Where-Object { $_ -notmatch "pylzma" } | Set-Content tools\edl\req_nolzma.txt
    & $PY -m pip install -r tools\edl\req_nolzma.txt -q
}

Write-Host "== 4/5  baixando adb/fastboot (platform-tools) ==" -ForegroundColor Cyan
if (-not (Test-Path "tools\platform-tools\adb.exe")) {
    Invoke-WebRequest "https://dl.google.com/android/repository/platform-tools-latest-windows.zip" -OutFile tools\pt.zip
    Expand-Archive tools\pt.zip -DestinationPath tools -Force
    Remove-Item tools\pt.zip
}

Write-Host "== 5/5  drivers (UsbDk, Google USB, Zadig) ==" -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path tools\drivers | Out-Null
if (-not (Test-Path "tools\drivers\UsbDk_x64.msi")) {
    Invoke-WebRequest "https://github.com/daynix/UsbDk/releases/download/v1.00-22/UsbDk_1.0.22_x64.msi" -OutFile tools\drivers\UsbDk_x64.msi
}
if (-not (Test-Path "tools\drivers\google\usb_driver\android_winusb.inf")) {
    Invoke-WebRequest "https://dl.google.com/android/repository/usb_driver_r13-windows.zip" -OutFile tools\drivers\g.zip
    Expand-Archive tools\drivers\g.zip -DestinationPath tools\drivers\google -Force
    Remove-Item tools\drivers\g.zip
}
if ((Test-Path "tools\edl\Drivers\Windows\zadig-2.8.exe") -and -not (Test-Path "tools\drivers\zadig.exe")) {
    Copy-Item tools\edl\Drivers\Windows\zadig-2.8.exe tools\drivers\zadig.exe
}

Write-Host "`nPronto! Rode:  pyenv\Scripts\python app.py" -ForegroundColor Green
Write-Host "Ou gere o .exe:  powershell -ExecutionPolicy Bypass -File build.ps1" -ForegroundColor Green
