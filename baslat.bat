@echo off
cls
echo ========================================================
echo       OtoEdit Sistemi Baslatiliyor...
echo ========================================================
echo.

REM Angular CLI Analytics promptunu kapat
set "NG_CLI_ANALYTICS=false"

echo [1/4] Eski acik servisler temizleniyor (Eger varsa)...
taskkill /F /IM "dotnet.exe" /T > nul 2>&1
taskkill /F /IM "node.exe" /T > nul 2>&1
taskkill /F /IM "OtoEdit.API.exe" /T > nul 2>&1
taskkill /FI "WINDOWTITLE eq OtoEdit-*" /F /T > nul 2>&1

REM Eger .env dosyasi yoksa ve .env.example varsa kopyala
if not exist "%~dp0.env" (
    if exist "%~dp0.env.example" (
        echo [.env] .env dosyasi bulunamadi, .env.example dosyasindan olusturuluyor...
        copy "%~dp0.env.example" "%~dp0.env" > nul
    )
)

REM Eger .env dosyasi varsa ortama aktar
if exist "%~dp0.env" (
    echo [.env] Ortam degiskenleri yukleniyor...
    for /f "usebackq tokens=1* delims==" %%a in (`findstr /v "^#" "%~dp0.env"`) do (
        if not "%%a"=="" set "%%a=%%b"
    )
)
echo.

echo [2/4] Docker servisleri baslatiliyor (PostgreSQL, Redis, RabbitMQ, MinIO, Python Worker)...
docker-compose -f "%~dp0docker-compose.dev.yml" up -d --wait

echo.
echo [3/4] Servislerin saglik durumlari kontrol ediliyor...
docker-compose -f "%~dp0docker-compose.dev.yml" ps

echo.
echo [3.5/4] Projeler derleniyor (dosya kilitlenme cakismasini onlemek icin)...
dotnet build "%~dp0OtoEdit.slnx" -c Debug
if %errorlevel% neq 0 (
    echo [HATA] Proje derlenemedi!
    pause
    exit /b %errorlevel%
)

echo.
echo [4/4] API, Worker ve Frontend pencereleri aciliyor...

start "OtoEdit-API" cmd /k "cd /d "%~dp0src\OtoEdit.API" && dotnet run --no-build"
start "OtoEdit-Worker" cmd /k "docker logs -f otoedit-dev-worker"
start "OtoEdit-UI" cmd /k "cd /d "%~dp0src\OtoEdit.Frontend" && npm start"

echo.
echo Tarayici aciliyor...
ping 127.0.0.1 -n 7 > nul
start http://localhost:4200
start http://localhost:5001/swagger

echo.
echo ========================================================
echo OtoEdit Sistemi Basariyla Baslatildi!
echo Arayuz:    http://localhost:4200
echo Swagger:   http://localhost:5001/swagger
echo MinIO:     http://localhost:9001 (minioadmin / minioadmin)
echo RabbitMQ:  http://localhost:15672 (guest / guest)
echo API Key:   SUPER_SECRET_OTOEDIT_KEY_123!
echo ========================================================
echo Bu pencereyi kapatabilirsiniz.
pause
