@echo off
setlocal

set "batdir=%~dp0"
set "productName=AnimRef"
set "developerName=Shirzad Bahrami"
set "websiteAddress=www.shirzadbahrami.com"
set "minVersion=2025"
set "maxVersion=2028"
set "productVer=1.0"
set "fileName=AnimRef.zip"
set "installationPath=%ProgramData%\Autodesk\ApplicationPlugins"

echo.
echo  ==================================================
echo    %productName% v%productVer%
echo    Developed by: %developerName%
echo    Website: %websiteAddress%
echo    Supported: 3ds Max %minVersion% - %maxVersion%
echo  ==================================================
echo.

if not exist "%batdir%%fileName%" (
    echo  ERROR: "%fileName%" not found next to this installer.
    echo  Make sure AnimRef.zip is in the same folder as this .bat file.
    echo.
    pause
    exit /b 1
)

echo  Press any key to install %productName% into:
echo  %installationPath%
echo.
pause

if not exist "%installationPath%" (
    mkdir "%installationPath%"
)

powershell -NoProfile -Command "Expand-Archive -Force '%batdir%%fileName%' '%installationPath%'"

if %errorlevel% neq 0 (
    echo.
    echo  ERROR: Installation failed. Try running this file as Administrator.
    echo.
    pause
    exit /b 1
)

echo.
echo  ==================================================
echo    %productName% installed successfully!
echo.
echo    How to launch:
echo      1. Open 3ds Max %minVersion% - %maxVersion%
echo      2. Press X to search, type "AnimRef"
echo      3. Click it or assign a keyboard shortcut
echo  ==================================================
echo.
timeout /t 5
endlocal