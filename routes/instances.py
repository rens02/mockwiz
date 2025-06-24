import os
import subprocess
import threading
from flask import Blueprint, session, jsonify


wiremock_processes = {}
instances_bp = Blueprint('instances', __name__)
def stream_logs(port):
    log_file_path = f'wiremock_instances/{port}/wiremock.log'
    os.makedirs(os.path.dirname(log_file_path), exist_ok=True)

    def log_stream(pipe):
        with open(log_file_path, 'a') as f:
            for line in iter(pipe.readline, b''):
                decoded_line = line.decode().strip()
                f.write(decoded_line + '\n')
    return log_stream

def start_wiremock(port):
    wiremock_dir = f'wiremock_instances/{port}'
    os.makedirs(wiremock_dir, exist_ok=True)
    cmd = [
        'java', '-jar', 'static/wiremock/wiremock-jre8-standalone-2.35.0.jar',
        '--port', str(port), '--root-dir', wiremock_dir
    ]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    thread = threading.Thread(target=stream_logs(port), args=(process.stdout,), daemon=True)
    thread.start()
    wiremock_processes[port] = process
@instances_bp.route('/start_instance', methods=['POST'])
def start_instance():
    port = session.get('current_port')
    if port and port not in wiremock_processes:
        start_wiremock(port)
        return jsonify({'success': True, 'message': f'Started Wiremock on port {port}.'})
    return jsonify({'success': False, 'message': 'Port not set or already running.'})

@instances_bp.route('/stop_instance', methods=['POST'])
def stop_instance():
    port = session.get('current_port')
    process = wiremock_processes.get(port)
    if process:
        try:
            # First try graceful termination
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # If still alive, force kill
                process.kill()
                process.wait(timeout=5)

            del wiremock_processes[port]
            return jsonify({'success': True, 'message': f'Stopped Wiremock on port {port}.'})
        except Exception as e:
            return jsonify({'success': False, 'message': f'Error stopping Wiremock: {str(e)}'})
    return jsonify({'success': False, 'message': 'No running instance found.'})