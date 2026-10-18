#!/bin/bash
echo "Starting Backend Server..."
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8088
