#!/bin/bash

# Start the app in the background
uvicorn app.main:app --host 0.0.0.0 --port 8000 &
APP_PID=$!

# Wait for the app to be ready
echo "Waiting for app to start..."
until curl -s http://localhost:8000/health >/dev/null; do
    sleep 1
done

# Run the seed endpoint
echo "Seeding data..."
curl -X POST http://localhost:8000/api/strava/seed

# Wait for the app process
wait $APP_PID
