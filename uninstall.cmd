@echo off
REM Windows: remove Antigravalgia.
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (py -3 -m antigravalgia.install uninstall) else (python -m antigravalgia.install uninstall)
