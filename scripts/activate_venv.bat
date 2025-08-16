@echo off
REM Activate the Python virtual environment for Command Prompt
REM Usage: scripts\activate_venv.bat

set VENV=%~dp0..\venv\Scripts\activate.bat
IF NOT EXIST "%VENV%" (
  echo Could not find %VENV%. Ensure the virtual environment exists.
  exit /b 1
)
call "%VENV%"
echo Virtual environment activated.
