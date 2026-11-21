@echo off
rem Cincinnati Rail hub launcher for Windows (cmd and PowerShell, which runs .cmd files under any execution policy).
rem Usage: .\crhub [command] [options]    With no command it serves. .\crhub --help lists the commands.
rem It runs "python -m region" through uv when uv is installed, else through .venv (see region\core\README.md).
setlocal
set "PYTHONUTF8=1"
set "CRHUB_ROOT=%~dp0"
where uv >nul 2>nul
if errorlevel 1 goto venv
uv run --locked --project "%CRHUB_ROOT%." python -m region %*
exit /b %ERRORLEVEL%

:venv
if not exist "%CRHUB_ROOT%.venv\Scripts\python.exe" goto none
"%CRHUB_ROOT%.venv\Scripts\python.exe" -m region %*
exit /b %ERRORLEVEL%

:none
echo crhub: found neither uv nor .venv\Scripts\python.exe. 1>&2
echo   With uv:    winget install --id astral-sh.uv -e   then  .\crhub setup 1>&2
echo   Without uv: py -3.12 -m venv .venv  then  .venv\Scripts\pip install -r requirements.lock -e . 1>&2
exit /b 1
