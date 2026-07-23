@echo off
title PeopleSoft ERD Explorer Launcher
echo ==================================================
echo         PeopleSoft ERD Explorer Setup
echo ==================================================
echo.

:: Start browser slightly before to ensure it opens immediately when Flask binds
start "" "http://127.0.0.1:5000"

echo [INFO] Launching PeopleSoft ERD Explorer...
echo [INFO] Running: python app.py
echo.

python app.py

pause
