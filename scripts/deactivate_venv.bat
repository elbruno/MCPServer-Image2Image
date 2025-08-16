@echo off
REM Deactivate the Python virtual environment for Command Prompt
REM Usage: scripts\deactivate_venv.bat

REM If using activate.bat from venv, this will restore original PATH and PROMPT
if defined VIRTUAL_ENV (
  call "%~dp0..\venv\Scripts\deactivate.bat"
  echo Virtual environment deactivated.
  goto :eof
)

echo No active virtual environment found (VIRTUAL_ENV not set).
exit /b 1
