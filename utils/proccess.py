import os
import json
import psutil

PID_TRACK_FILE = "wiremock_pids.json"

def save_pid(port, pid):
    pids = {}
    if os.path.exists(PID_TRACK_FILE):
        with open(PID_TRACK_FILE, 'r') as f:
            pids = json.load(f)
    pids[str(port)] = pid
    with open(PID_TRACK_FILE, 'w') as f:
        json.dump(pids, f)

def remove_pid(port):
    if not os.path.exists(PID_TRACK_FILE):
        return
    with open(PID_TRACK_FILE, 'r') as f:
        pids = json.load(f)
    if str(port) in pids:
        del pids[str(port)]
    with open(PID_TRACK_FILE, 'w') as f:
        json.dump(pids, f)

def get_pids():
    if not os.path.exists(PID_TRACK_FILE):
        return {}
    with open(PID_TRACK_FILE, 'r') as f:
        return json.load(f)

def cleanup_dead_pids():
    # Remove entries for processes no longer running
    pids = get_pids()
    updated = {port: pid for port, pid in pids.items() if psutil.pid_exists(pid)}
    with open(PID_TRACK_FILE, 'w') as f:
        json.dump(updated, f)
    return updated
