#!/usr/bin/env python3
import subprocess
import sys

print("Starting backend server...")

cmd = [
    sys.executable,
    "-m",
    "uvicorn",
    "codebase_driven_agent.main:app",
    "--host",
    "0.0.0.0",
    "--port",
    "7000",
]

process = subprocess.Popen(cmd)
print(f"Backend server started on http://localhost:7000")
print(f"API docs: http://localhost:7000/docs")

try:
    process.wait()
except KeyboardInterrupt:
    print("\nShutting down server...")
    process.terminate()
    process.wait()
    print("Server stopped")
