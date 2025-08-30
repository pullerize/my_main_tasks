@echo off
echo Starting 8bit-codex backend server...
cd agency_backend
echo Using database: /home/pullerize/8bit_db/app.db
uvicorn app.main:app --reload --port 8000 --host 127.0.0.1
pause