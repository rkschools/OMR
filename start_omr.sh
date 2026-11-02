#!/bin/bash
echo "====================================="
echo "   STARTING RISE OMR PLATFORM 2027"
echo "====================================="

# Trap SIGINT to kill all background processes
trap "trap - SIGTERM && kill -- -$$" SIGINT SIGTERM EXIT

# 1. Start Firebase Emulators
echo "[1] Starting Firebase Local Emulators..."
export JAVA_HOME=$(pwd)/jdk-21.0.1.jdk/Contents/Home
export PATH=$JAVA_HOME/bin:$PATH
npx -y firebase-tools emulators:start --only auth,firestore > OMR_SCAN/emulator.log 2>&1 &
sleep 5

# 2. Start FastAPI Backend
echo "[2] Starting FastAPI Backend Engine..."
source venv/bin/activate
python3 api.py > OMR_SCAN/api.log 2>&1 &
sleep 2

# 3. Start Scan Ingestion Service
echo "[3] Starting Automatic Scan Ingestion Service..."
python3 scan_ingestion_service.py > OMR_SCAN/ingestion.log 2>&1 &

# 4. Start React Frontend
echo "[4] Starting React Dashboard..."
cd frontend
npm run dev &
cd ..

echo ""
echo "====================================="
echo "   SYSTEM IS ONLINE AND RUNNING"
echo "====================================="
echo "Dashboard UI: http://localhost:5173"
echo "Backend API:  http://localhost:8000"
echo "Emulator UI:  http://localhost:4000"
echo "Scanner Drop: $(pwd)/OMR_SCAN/inbox/"
echo "====================================="
echo "Press Ctrl+C to stop all services."

wait
