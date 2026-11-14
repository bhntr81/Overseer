@echo off
rem Double-click after downloading Overseer: puts Overseer on your Desktop.
rem First it tries to build Overseer.exe (one file, Python bundled); if that is not
rem possible it makes a Desktop shortcut that opens the window with your Python.
setlocal
cd /d "%~dp0"
echo Overseer: building Overseer.exe ...
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build-exe.ps1
if not errorlevel 1 (
    copy /y dist\Overseer.exe "%USERPROFILE%\Desktop\Overseer.exe" >nul
    echo Done: Overseer.exe is on your Desktop.
    pause
    exit /b 0
)
echo Could not build the .exe; making a Desktop shortcut instead ...
py -3 -c "from overseer.gui import install_shortcut; print(install_shortcut())"
if errorlevel 1 (
    echo Python 3 is needed. Install it from https://www.python.org/downloads/ and run this again.
    pause
    exit /b 1
)
echo Done: the Overseer shortcut is on your Desktop.
pause
