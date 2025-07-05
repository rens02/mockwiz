import os
import subprocess
import threading
import json
import psutil
import queue

PID_TRACK_FILE = "wiremock_pids.json"
from config import WIREMOCK_JAR_NAME
import signal

WIREMOCK_JAR_PATH = f"static/wiremock/{WIREMOCK_JAR_NAME}"

class WiremockManager:
    def __init__(self):
        self.processes = {}  # {port: process_object}
        self.output_queues = {} # {port: queue.Queue()}
        self.restore_processes_on_startup()

    def _save_pid(self, port, pid):
        pids = {}
        if os.path.exists(PID_TRACK_FILE):
            with open(PID_TRACK_FILE, 'r') as f:
                pids = json.load(f)
        pids[str(port)] = pid
        with open(PID_TRACK_FILE, 'w') as f:
            json.dump(pids, f)

    def _remove_pid(self, port):
        if not os.path.exists(PID_TRACK_FILE):
            return
        with open(PID_TRACK_FILE, 'r') as f:
            pids = json.load(f)
        if str(port) in pids:
            del pids[str(port)]
        with open(PID_TRACK_FILE, 'w') as f:
            json.dump(pids, f)

    def _get_pids(self):
        if not os.path.exists(PID_TRACK_FILE):
            return {}
        with open(PID_TRACK_FILE, 'r') as f:
            return json.load(f)

    def _cleanup_dead_pids(self):
        if not os.path.exists(PID_TRACK_FILE):
            return {}
        with open(PID_TRACK_FILE, 'r') as f:
            pids = json.load(f)
        updated = {}
        for port, pid in pids.items():
            try:
                p = psutil.Process(pid)
                # Check if the process is running and is a WireMock instance
                if p.is_running() and any(WIREMOCK_JAR_PATH in s for s in p.cmdline()):
                    updated[port] = pid
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass  # process dead or inaccessible
        with open(PID_TRACK_FILE, 'w') as f:
            json.dump(updated, f)
        return updated

    def _stream_logs(self, port, q, pipe):
        log_file_path = f'wiremock_instances/{port}/wiremock.log'
        os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
        with open(log_file_path, 'a') as f:
            for line in iter(pipe.readline, b''):
                decoded_line = line.decode().strip()
                f.write(decoded_line + '\n')
                q.put(decoded_line + '\n')

    def start_wiremock(self, port):
        port_str = str(port)
        if port_str in self.processes and self.processes[port_str].poll() is None:
            return False, f"Wiremock is already running on port {port}."

        wiremock_dir = f'wiremock_instances/{port}'
        os.makedirs(wiremock_dir, exist_ok=True)
        cmd = [
            'java', '-jar', WIREMOCK_JAR_PATH,
            '--port', port_str, '--root-dir', wiremock_dir
        ]
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            )
            self.processes[port_str] = process
            self._save_pid(port_str, process.pid)

            q = queue.Queue()
            self.output_queues[port_str] = q
            threading.Thread(target=self._stream_logs, args=(port_str, q, process.stdout), daemon=True).start()
            return True, f"Started Wiremock on port {port}."
        except Exception as e:
            return False, f"Failed to start Wiremock on port {port}: {e}"

    # def stop_wiremock(self, port):
    #     port_str = str(port)
    #     process = self.processes.get(port_str)
    #     if process:
    #         os.kill(process.pid, signal.CTRL_BREAK_EVENT)
    #         try:
    #             # Terminate the entire process group
    #             process.wait(timeout=5)
    #         except subprocess.TimeoutExpired:
    #             # If it doesn't terminate, kill the entire process group forcefully
    #             process.kill()
    #             process.wait(timeout=5)
    #         self._remove_pid(port_str)
    #         del self.processes[port_str]
    #         if port_str in self.output_queues:
    #             del self.output_queues[port_str]
    #         return True, f"Stopped Wiremock on port {port}."
    #     return False, "No running instance found for this port."

    def stop_wiremock(self, port):
        port_str = str(port)
        process = self.processes.get(port_str)
        if process:
            try:
                # Use psutil to get the full process tree and kill all children
                parent = psutil.Process(process.pid)
                children = parent.children(recursive=True)
                for child in children:
                    child.kill()
                parent.kill()

                parent.wait(5)
            except Exception as e:
                return False, f"Error stopping WireMock on port {port}: {e}"

            self._remove_pid(port_str)
            del self.processes[port_str]
            if port_str in self.output_queues:
                del self.output_queues[port_str]
            return True, f"Stopped WireMock on port {port}."

        return False, "No running instance found for this port."

    def is_running(self, port):
        port_str = str(port)
        return port_str in self.processes and self.processes[port_str].poll() is None

    def restore_processes_on_startup(self):
        pids = self._cleanup_dead_pids()
        for port, pid in pids.items():
            try:
                proc = psutil.Process(pid)
                self.processes[port] = proc
                # Re-attach log streaming if possible, or at least acknowledge the process
                q = queue.Queue()
                self.output_queues[port] = q
                # Note: Cannot easily re-attach to stdout of an already running process
                # For now, just acknowledge it's running.
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                self._remove_pid(port) # Clean up if process is truly gone
                pass

    def get_log_output(self, port):
        port_str = str(port)
        if port_str in self.output_queues:
            q = self.output_queues[port_str]
            lines = []
            while not q.empty():
                lines.append(q.get_nowait())
            return "".join(lines)
        return ""
