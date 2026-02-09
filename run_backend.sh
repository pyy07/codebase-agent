#!/usr/bin/env python3
import subprocess
import sys

print("Starting backend server...")

cmd = [sys.executable, "-m", "uvicorn", "codebase_driven_agent.main:app", "--host", "0.0.0.0", "--port", "7000"]

try:
    process = subprocess.Popen(cmd)
    print(f"Backend server started on http://localhost:7000")
    print(f"API docs: http://localhost:7000/docs")
    
    process.wait()
    
except KeyboardInterrupt:
    print("\nShutting down server...")
    process.terminate()
    try:
        process.wait()
    except:
        pass
    print("Server stopped")
    sys.exit(0)
except Exception as e:
    print(f"Error starting server: {str(e)}")
    sys.exit(1)
