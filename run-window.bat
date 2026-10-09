@echo off
echo Starting Tower Defense...

@REM Check for existing Miniconda/Anaconda to activate base environment
if exist "%USERPROFILE%\Miniconda3\Scripts\activate.bat" (
    call "%USERPROFILE%\Miniconda3\Scripts\activate.bat"
) else if exist "%USERPROFILE%\Anaconda3\Scripts\activate.bat" (
    call "%USERPROFILE%\Anaconda3\Scripts\activate.bat"
)

call conda activate tower_defense
if %errorlevel% neq 0 (
    echo Failed to activate environment. Have you run install.bat?
    pause
    exit /b
)

python main.py

@REM Wait for user to close the game using "pause" command
@REM pause
