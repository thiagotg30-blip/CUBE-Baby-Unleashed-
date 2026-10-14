@echo off
cd /d "%~dp0"
call setup.bat
if errorlevel 1 ( pause & exit /b 1 )
".venv\Scripts\python.exe" main.py
echo.
echo Se deu erro, ele tambem fica em %USERPROFILE%\CUBEBabyUnleashed\crash.log
pause
