@echo off
REM Runs the LISM backup and keeps a log of every attempt.
REM
REM Called by the Windows scheduled task "LISM Weekly Backup". Safe to
REM double-click as well, to take a backup on the spot.
REM
REM The database connection string is read from backend\.env, which is
REM gitignored and never leaves this machine.

setlocal
cd /d "%~dp0.."

set "BACKUP_DIR=%USERPROFILE%\OneDrive\Documents\LISM Backups"
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

echo. >> "%BACKUP_DIR%\backup-log.txt"
echo ===== %DATE% %TIME% ===== >> "%BACKUP_DIR%\backup-log.txt"

".venv\Scripts\python.exe" "scripts\backup.py" >> "%BACKUP_DIR%\backup-log.txt" 2>&1

if errorlevel 1 (
  echo BACKUP FAILED - see the log above >> "%BACKUP_DIR%\backup-log.txt"
  exit /b 1
)
exit /b 0
