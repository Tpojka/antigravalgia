@echo off
REM Windows: install Antigravalgia (see antigravalgia\install).
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (py -3 -m antigravalgia.install %*) else (python -m antigravalgia.install %*)
