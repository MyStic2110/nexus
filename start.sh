#!/bin/bash
# Start the Cricbuzz surveillance agent in background
python scripts/auto_agent_cricbuzz.py &

# Start the main FastAPI server with auto-reload (foreground)
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
