@echo off
rem Mine Grox through the public P2Pool node pool.groxcoin.com (beta). No Grox node needed.
rem Payouts go straight to your address inside each block the pool finds.
rem Put your Grox address (starts with G) after WALLET= below, or paste it when asked.
set WALLET=PUT_YOUR_GROX_ADDRESS_HERE
set POOL=pool.groxcoin.com:3333

cd /d "%~dp0"
if "%WALLET:~0,1%" NEQ "G" set /p WALLET=Paste your Grox address (starts with G) and press Enter: 
if "%WALLET:~0,1%" NEQ "G" (
  echo That is not a Grox address.
  pause
  exit /b 1
)
xmrig.exe -o %POOL% -a rx/grox -u %WALLET% %*
pause
