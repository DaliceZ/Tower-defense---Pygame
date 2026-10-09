@echo off
setlocal
echo Checking for Conda...


if exist "%USERPROFILE%\Miniconda3\Scripts\conda.exe" (
    echo Miniconda found in default location.
    set "PATH=%USERPROFILE%\Miniconda3\condabin;%USERPROFILE%\Miniconda3\Scripts;%PATH%"
    goto :conda_found
)

where conda >nul 2>&1
if %errorlevel% neq 0 (
    echo Conda not found.
    echo Downloading Miniconda...
    curl https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe --output Miniconda3-latest-Windows-x86_64.exe

    echo Installing Miniconda ^(Silent - Adding to PATH^)...
    echo IMPORTANT: Please wait for the installation to complete.
    start /wait "" Miniconda3-latest-Windows-x86_64.exe /InstallationType=JustMe /RegisterPython=1 /AddToPath=1 /S /D=%UserProfile%\Miniconda3

    echo ==========================================================
    echo Miniconda installation finished!
    echo.
    echo Please run this script again to install game dependencies.
    echo ==========================================================
    del Miniconda3-latest-Windows-x86_64.exe
    pause
    exit /b
)


:conda_found
echo Conda found.

call conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main
call conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r
call conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/msys2

echo Creating/Updating virtual environment 'tower_defense'...
call conda create -n tower_defense python=3.12 -y

echo Activating virtual environment...
call conda activate tower_defense

echo Installing dependencies...
pip install pygame==2.6.1

echo ======================
echo Installation Complete!
echo ======================
echo To start the game.
echo.
echo Run "run-window.bat"
echo ======================
pause
