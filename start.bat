@echo off
cd /d "%~dp0app"
pip install -r requirements.txt -q
python app.py
pause
