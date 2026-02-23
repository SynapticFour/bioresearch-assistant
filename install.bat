@echo off
echo BioResearch Assistant - Installer v1.3.0
echo Synaptic Four GmbH
echo.

where python >nul 2>&1
if %errorlevel% neq 0 (
    echo Python nicht gefunden.
    echo Bitte installieren: https://python.org
    pause
    exit /b 1
)

python -m pip install psutil --quiet 2>nul
python install.py %*
pause
