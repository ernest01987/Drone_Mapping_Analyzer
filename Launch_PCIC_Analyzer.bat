@echo off
REM ============================================================
REM  PCIC Drone 3D Farm Area Analyzer — Windows Launcher
REM ============================================================

setlocal
cd /d "%~dp0"

set APP_DIR=%~dp0pcic_analyzer

if exist "%~dp0pcic_env\Scripts\python.exe" (
    set "PYTHON_EXE=%~dp0pcic_env\Scripts\python.exe"
) else if exist "%~dp0.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
) else if exist "%~dp0venv\Scripts\python.exe" (
    set "PYTHON_EXE=%~dp0venv\Scripts\python.exe"
) else (
    echo.
    echo =========================================================
    echo  [ERROR] Virtual environment not found!
    echo =========================================================
    echo  Please create and setup your virtual environment first:
    echo.
    echo    python -m venv pcic_env
    echo    pcic_env\Scripts\activate
    echo    python -m pip install --upgrade pip
    echo    pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

echo.
echo =========================================================
echo   PCIC Drone 3D Farm Area Analyzer
echo =========================================================
echo.
echo Launching Streamlit application...
echo Open your browser at: http://localhost:8501
echo.

"%PYTHON_EXE%" -m streamlit run "%APP_DIR%\app.py" --server.port 8501 --server.headless false --server.maxUploadSize 2048

pause
