@echo off

set productName=AnimRef
set developerName=Shirzad Bahrami
set websiteAddress=www.shirzadbahrami.com

set minVersion=2018
set maxVersion=2025

set productVer=1.5.2

set releaseDate=2020-10-17
set lastUpdate=2024-09-02

set fileName=AnimRef.zip
set installationPath=/Autodesk/ApplicationPlugins

echo %productName% Developed By: %developerName%
echo Version: %productVer%
echo Website: %websiteAddress%
echo.
echo Supported Version: %minVersion% - %maxVersion%
echo Release: %releaseDate%
echo Update: %lastUpdate%

echo.
pause>nul|set/p =Press Any Key To Install "%productName%" On 3Ds Max From "%minVersion%" to "%maxVersion%"...
echo.
cls

powershell -Command "Expand-Archive -Force "%batdir%%fileName% "%ProgramData%%installationPath%" "

echo "%productName%" Installed successfully, Hope You Enjoy...
ping -n 4 localhost >nul
