@echo off
setlocal
cd /d "%~dp0"
rem Check dependencies in the interpreter that will actually run the server.
set "PESQUISA_PYTHON=%~dp0.venv\Scripts\python.exe"
if exist "%PESQUISA_PYTHON%" (
    "%PESQUISA_PYTHON%" scripts\ambiente.py --silencioso >nul 2>&1
    if not errorlevel 1 goto iniciar
)
set "PESQUISA_PYTHON=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if exist "%PESQUISA_PYTHON%" (
    "%PESQUISA_PYTHON%" scripts\ambiente.py --silencioso >nul 2>&1
    if not errorlevel 1 goto iniciar
)
set "PESQUISA_PYTHON=python"
python scripts\ambiente.py --silencioso >nul 2>&1
if not errorlevel 1 goto iniciar
py -3 scripts\ambiente.py --silencioso >nul 2>&1
if not errorlevel 1 goto iniciar_py
echo Nao foi encontrado Python 3.12+ com SQLite/FTS5, pypdf, python-docx e reportlab disponiveis.
echo Prepare as dependencias de requirements.txt no Python escolhido ou use o runtime do Codex.
if "%APURACAO_OCULTO%"=="1" powershell -NoProfile -Command "Add-Type -AssemblyName PresentationFramework; [System.Windows.MessageBox]::Show('Nao foi encontrado um ambiente Python completo para a Mesa. Abra Iniciar pesquisa.cmd para ver o diagnostico.','Mesa de apuracao')" >nul
goto fim
:iniciar
if "%~1"=="--verificar-runtime" (
    "%PESQUISA_PYTHON%" scripts\ambiente.py
    goto fim
)
"%PESQUISA_PYTHON%" scripts\interface_pesquisa.py %*
goto fim
:iniciar_py
if "%~1"=="--verificar-runtime" (
    py -3 scripts\ambiente.py
    goto fim
)
py -3 scripts\interface_pesquisa.py %*
:fim
if "%APURACAO_OCULTO%"=="1" exit /b
pause
