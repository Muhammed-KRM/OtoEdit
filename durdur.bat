@echo off
cls
echo ========================================================
echo       OtoEdit Sistemi Durduruluyor...
echo ========================================================
echo.

echo Docker servisleri durduruluyor...
cd /d "%~dp0"
docker-compose -f docker-compose.dev.yml stop

echo.
echo Calisan konsol pencereleri ve prosesler kapatiliyor...
taskkill /FI "WINDOWTITLE eq OtoEdit-API*" /F /T > nul 2>&1
taskkill /FI "WINDOWTITLE eq OtoEdit-Worker*" /F /T > nul 2>&1
taskkill /FI "WINDOWTITLE eq OtoEdit-UI*" /F /T > nul 2>&1
taskkill /F /IM "dotnet.exe" /T > nul 2>&1
taskkill /F /IM "node.exe" /T > nul 2>&1
taskkill /F /IM "OtoEdit.API.exe" /T > nul 2>&1

echo.
echo ========================================================
echo OtoEdit Sistemi basariyla durduruldu.
echo ========================================================
pause
