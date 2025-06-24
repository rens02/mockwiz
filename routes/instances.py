import threading
import subprocess
import os

import psutil
from flask import Blueprint, session, jsonify
from utils.proccess import save_pid, remove_pid, get_pids, cleanup_dead_pids
import queue

instances_bp = Blueprint('instances', __name__)
processes = {}       # {port: process}
output_queues = {}   # {port: queue.Queue()}

def stream_logs(port, q):
    log_file_path = f'wiremock_instances/{port}/wiremock.log'
    os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
    def log_stream(pipe):
        with open(log_file_path, 'a') as f:
            for line in iter(pipe.readline, b''):
                decoded_line = line.decode().strip()
                f.write(decoded_line + '\n')
                q.put(decoded_line + '\n')
    return log_stream

def start_wiremock(port):
    wiremock_dir = f'wiremock_instances/{port}'
    os.makedirs(wiremock_dir, exist_ok=True)
    cmd = [
        'java', '-jar', 'static/wiremock/wiremock-jre8-standalone-2.35.0.jar',
        '--port', str(port), '--root-dir', wiremock_dir
    ]
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
    )
    save_pid(port, process.pid)  # <-- Don't forget this!
    return process

def stop_wiremock(port):
    process = processes.get(port)
    if process:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        remove_pid(port)
        del processes[port]
        del output_queues[port]

def restore_processes_on_startup():
    pids = cleanup_dead_pids()
    for port, pid in pids.items():
        if psutil.pid_exists(pid):
            # Note: Cannot fully re-attach stdout pipes to already-running Java procs,
            # but you can let users kill/restart them, and tail logs from disk if needed.
            processes[port] = psutil.Process(pid)
restore_processes_on_startup()

@instances_bp.route('/start_instance', methods=['POST'])
def start_instance():
    port = session.get('current_port')
    if port and str(port) not in processes:
        start_wiremock(port)
        return jsonify({'success': True, 'message': f'Started Wiremock on port {port}.'})
    return jsonify({'success': False, 'message': 'Port not set or already running.'})


@instances_bp.route('/stop_instance', methods=['POST'])
def stop_instance():
    port = session.get('current_port')
    if port and str(port) in processes:
        stop_wiremock(port)
        return jsonify({'success': True, 'message': f'Stopped Wiremock on port {port}.'})
    return jsonify({'success': False, 'message': 'No running instance found.'})
