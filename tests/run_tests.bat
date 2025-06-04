@echo off
REM Script batch para ejecutar tests en Windows
REM Big Data Pipeline Testing Suite

echo.
echo ===================================================
echo 🚀 Big Data Pipeline - Testing Suite
echo ===================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python no está instalado o no está en el PATH
    pause
    exit /b 1
)

REM Navigate to project root
cd /d "%~dp0\.."

REM Show menu
:menu
echo.
echo Selecciona una opción:
echo.
echo 1. Instalar dependencias de testing
echo 2. Ejecutar tests rápidos (recomendado)
echo 3. Ejecutar todos los tests
echo 4. Ejecutar tests de Lambda
echo 5. Ejecutar tests de Glue Jobs
echo 6. Ejecutar tests de EMR
echo 7. Ejecutar tests de integración
echo 8. Generar reporte de coverage
echo 9. Ejecutar tests en paralelo
echo 10. Ejecutar checks de calidad
echo 11. Limpiar artefactos de testing
echo 12. Ejecutar tests específicos (patrón)
echo 0. Salir
echo.

set /p choice="Ingresa tu opción (0-12): "

if "%choice%"=="0" goto :end
if "%choice%"=="1" goto :install_deps
if "%choice%"=="2" goto :fast_tests
if "%choice%"=="3" goto :all_tests
if "%choice%"=="4" goto :lambda_tests
if "%choice%"=="5" goto :glue_tests
if "%choice%"=="6" goto :emr_tests
if "%choice%"=="7" goto :integration_tests
if "%choice%"=="8" goto :coverage
if "%choice%"=="9" goto :parallel_tests
if "%choice%"=="10" goto :quality_checks
if "%choice%"=="11" goto :clean
if "%choice%"=="12" goto :specific_tests

echo ❌ Opción inválida
goto :menu

:install_deps
echo.
echo 📦 Instalando dependencias de testing...
python tests/run_tests.py --install-deps
pause
goto :menu

:fast_tests
echo.
echo ⚡ Ejecutando tests rápidos...
python tests/run_tests.py --fast
pause
goto :menu

:all_tests
echo.
echo 🚀 Ejecutando todos los tests...
python tests/run_tests.py --all
pause
goto :menu

:lambda_tests
echo.
echo λ Ejecutando tests de Lambda...
python tests/run_tests.py --lambda
pause
goto :menu

:glue_tests
echo.
echo 🔧 Ejecutando tests de Glue Jobs...
python tests/run_tests.py --glue
pause
goto :menu

:emr_tests
echo.
echo ⚡ Ejecutando tests de EMR...
python tests/run_tests.py --emr
pause
goto :menu

:integration_tests
echo.
echo 🔗 Ejecutando tests de integración...
python tests/run_tests.py --integration
pause
goto :menu

:coverage
echo.
echo 📊 Generando reporte de coverage...
python tests/run_tests.py --coverage
echo.
echo 📋 Reporte generado en: tests\htmlcov\index.html
pause
goto :menu

:parallel_tests
echo.
echo 🏃‍♂️ Ejecutando tests en paralelo...
python tests/run_tests.py --parallel
pause
goto :menu

:quality_checks
echo.
echo ✨ Ejecutando checks de calidad...
python tests/run_tests.py --quality
pause
goto :menu

:clean
echo.
echo 🧹 Limpiando artefactos de testing...
python tests/run_tests.py --clean
pause
goto :menu

:specific_tests
echo.
set /p pattern="Ingresa el patrón de tests a ejecutar: "
echo.
echo 🎯 Ejecutando tests con patrón: %pattern%
python tests/run_tests.py -k "%pattern%"
pause
goto :menu

:end
echo.
echo 👋 ¡Hasta luego!
echo. 