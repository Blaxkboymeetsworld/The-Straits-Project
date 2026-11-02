@echo off
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
where python >nul 2>nul && (python straits_project.py) || (py straits_project.py)
pause
