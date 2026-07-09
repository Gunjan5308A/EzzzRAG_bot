#!/usr/bin/env python3
"""Entry point that survives terminal death."""
import subprocess, sys, time, signal, os

LOG = "/tmp/rag.log"
PID = "/tmp/rag.pid"

def cleanup(*_):
    try: os.unlink(PID)
    except: pass
    sys.exit(0)

signal.signal(signal.SIGTERM, cleanup)
signal.signal(signal.SIGINT, cleanup)

with open(LOG, "w") as log:
    proc = subprocess.Popen(
        [sys.executable, "-B", "app.py"],
        stdout=log, stderr=log,
        cwd=os.path.dirname(os.path.abspath(__file__)),
        start_new_session=True
    )

with open(PID, "w") as f:
    f.write(str(proc.pid))

print(f"Server started (PID {proc.pid})")
print(f"Log: {LOG}")
print(f"URL: http://localhost:8000")
