@echo off
REM Simple startup script for Image-to-Goods

REM 1. Create virtual environment if it doesn't exist
if not exist "venv" (
    python -m venv venv
)

REM 2. Activate virtual environment
call venv\Scripts\activate.bat

REM 3. Install dependencies (optional - only if needed)
REM pip install -r requirements.txt

REM 4. Run the app
c:\Users\yujin\Desktop\aiweb_clicker_retry\venv\Scripts\python.exe -m app

pause
