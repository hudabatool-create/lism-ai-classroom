@echo off
REM Who has actually used LISM -- not who signed up, who ran a real session.
REM
REM Double-click to run. Reads the database connection from backend\.env,
REM which stays on this machine.

setlocal
cd /d "%~dp0.."

".venv\Scripts\python.exe" "scripts\usage.py"

echo.
echo ----------------------------------------------------------------
echo A teacher who signed up but never ran a session with students in
echo it has not tried LISM -- they opened the page and stopped.
echo ----------------------------------------------------------------
echo.
pause
