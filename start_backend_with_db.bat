@echo off
set SQLALCHEMY_DATABASE_URL=sqlite:////home/pullerize/8bit_db/app.db
cd agency_backend
uvicorn app.main:app --reload --port 8000 --host 127.0.0.1