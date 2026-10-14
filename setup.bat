@echo off
REM Cria um ambiente isolado com Python 3.12 e instala as dependencias.
REM (O Python 3.14 ainda nao tem pacote pronto do python-rtmidi no Windows.)
cd /d "%~dp0"
py -3.12 --version >nul 2>&1
if errorlevel 1 goto :nopy
if not exist ".venv\Scripts\python.exe" (
  py -3.12 -m venv .venv
  if errorlevel 1 goto :fail
)
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install --only-binary=:all: -r requirements.txt
if errorlevel 1 goto :fail
exit /b 0
:nopy
echo.
echo Python 3.12 nao encontrado. Instale com um destes:
echo   winget install Python.Python.3.12
echo   ou baixe em https://www.python.org/downloads/ (versao 3.12.x)
echo Depois rode este arquivo de novo.
exit /b 1
:fail
echo.
echo ERRO na instalacao. Copie as mensagens acima e me mande.
exit /b 1
