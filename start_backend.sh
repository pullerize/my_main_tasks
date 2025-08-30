#!/bin/bash
cd agency_backend
export SQLALCHEMY_DATABASE_URL="sqlite:////home/pullerize/8bit_db/app.db"
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000