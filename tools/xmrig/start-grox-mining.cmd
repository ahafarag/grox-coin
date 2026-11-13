@echo off
rem Solo-mine Grox with XMRig. Needs the Grox Wallet app (or groxd) running on this computer.
rem 1. Put your Grox address (starts with G) below, after WALLET=
rem 2. In the Grox Wallet app press Stop mining (XMRig does the mining now).
rem 3. Double-click this file.
set WALLET=PUT_YOUR_GROX_ADDRESS_HERE
set NODE=127.0.0.1:19881

cd /d "%~dp0"
if "%WALLET:~0,1%" NEQ "G" (
  echo Edit start-grox-mining.cmd in Notepad and put your Grox address ^(starts with G^) after WALLET=
  pause
  exit /b 1
)
xmrig.exe --daemon -o %NODE% -a rx/grox --coin GROX -u %WALLET% %*
pause
