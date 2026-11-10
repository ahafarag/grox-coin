# Builds the Windows wallet: GroxWallet.exe (PyInstaller) + installer (Inno Setup) + portable zip.
#
#   powershell -ExecutionPolicy Bypass -File windows\build.ps1 -BinDir <folder with groxd.exe ...>
#
# Needs Python 3.12 and Inno Setup 6 (iscc.exe). The groxd.exe / grox-wallet-rpc.exe /
# grox-wallet-cli.exe binaries come from the "windows" GitHub workflow (cross-compiled
# from this repository) or from your own build.
param(
  [string]$BinDir = "build\win\bin",
  [string]$Version = "",
  [string]$OutDir = "dist"
)
$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root
if (-not $Version) { $Version = (Get-Content release\VERSION -Raw).Trim() }
$BinDir = Resolve-Path $BinDir
New-Item -ItemType Directory -Force $OutDir | Out-Null
$OutDir = Resolve-Path $OutDir
$Work = Join-Path $Root "build\windows"
Remove-Item -Recurse -Force $Work -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $Work | Out-Null

foreach ($f in "groxd.exe", "grox-wallet-rpc.exe", "grox-wallet-cli.exe") {
  if (-not (Test-Path (Join-Path $BinDir $f))) { throw "$f is missing in $BinDir" }
}

Write-Host "==> Python packages"
python -m pip install --disable-pip-version-check -q -r windows\requirements.txt
if ($LASTEXITCODE) { throw "pip install failed" }

# file properties shown in Explorer / Task Manager
$v = ($Version.Split(".") + @("0", "0", "0", "0"))[0..3] -join ", "
$VersionInfo = @"
VSVersionInfo(
  ffi=FixedFileInfo(filevers=($v), prodvers=($v)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('CompanyName', 'Grox'),
      StringStruct('FileDescription', 'Grox Wallet'),
      StringStruct('FileVersion', '$Version'),
      StringStruct('InternalName', 'GroxWallet'),
      StringStruct('LegalCopyright', 'BSD-3-Clause'),
      StringStruct('OriginalFilename', 'GroxWallet.exe'),
      StringStruct('ProductName', 'Grox Wallet'),
      StringStruct('ProductVersion', '$Version')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"@
[IO.File]::WriteAllText((Join-Path $Work "version.txt"), $VersionInfo)  # no BOM, PyInstaller can't read one

Write-Host "==> GroxWallet.exe"
$sep = [IO.Path]::PathSeparator
python -m PyInstaller --noconfirm --clean --windowed --name GroxWallet `
  --icon (Join-Path $Root "windows\grox.ico") `
  --version-file (Join-Path $Work "version.txt") `
  --add-data "$(Join-Path $Root 'tools\wallet-app\index.html')$($sep)." `
  --add-data "$(Join-Path $Root 'windows\grox.ico')$($sep)." `
  --add-data "$(Join-Path $Root 'release\VERSION')$($sep)." `
  --paths (Join-Path $Root "tools\wallet-app") `
  --distpath (Join-Path $Work "dist") --workpath (Join-Path $Work "pyi") --specpath $Work `
  (Join-Path $Root "windows\grox_wallet.py")
if ($LASTEXITCODE) { throw "PyInstaller failed" }

$App = Join-Path $Work "dist\GroxWallet"
New-Item -ItemType Directory -Force (Join-Path $App "bin") | Out-Null
Copy-Item (Join-Path $BinDir "*.exe") (Join-Path $App "bin")
Get-ChildItem $BinDir -Filter *.dll -ErrorAction SilentlyContinue | Copy-Item -Destination (Join-Path $App "bin")
Copy-Item LICENSE (Join-Path $App "LICENSE.txt")
Copy-Item windows\README.txt (Join-Path $App "README.txt")

Write-Host "==> Portable zip"
$Zip = Join-Path $OutDir "GroxWallet-$Version-win-x64-portable.zip"
Remove-Item $Zip -ErrorAction SilentlyContinue
Compress-Archive -Path $App -DestinationPath $Zip

Write-Host "==> Installer"
$Iscc = (Get-Command iscc.exe -ErrorAction SilentlyContinue).Source
if (-not $Iscc) { $Iscc = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" }
if (-not (Test-Path $Iscc)) { throw "Inno Setup 6 (iscc.exe) not found. Install it: choco install innosetup" }
& $Iscc /Qp "/DAppVersion=$Version" "/DSourceDir=$App" "/DOutputDir=$OutDir" windows\installer.iss
if ($LASTEXITCODE) { throw "Inno Setup failed" }

Get-ChildItem $OutDir -File | Where-Object { $_.Name -like "GroxWallet-*" -and $_.Extension -ne ".sha256" } | ForEach-Object {
  $h = (Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLower()
  "$h  $($_.Name)" | Set-Content -NoNewline -Encoding ascii "$($_.FullName).sha256"
  Write-Host "$h  $($_.Name)"
}
