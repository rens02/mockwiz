import os
import subprocess
import threading
import json
import psutil

PID_TRACK_FILE = "wiremock_pids.json"
from config import WIREMOCK_JAR_NAME
import signal

WIREMOCK_JAR_PATH = f"static/wiremock/{WIREMOCK_JAR_NAME}"

class WiremockManager:
    def __init__(self) -> None:
        """
        Initializes the WiremockManager, restoring any previously running processes.
        """
        self.processes: dict[str, subprocess.Popen | psutil.Process] = {}
        self.restore_processes_on_startup()

    def _save_pid(self, port: str | int, pid: int) -> None:
        """
        Saves the PID of a WireMock instance to the tracking file.

        Args:
            port: The port of the WireMock instance.
            pid: The PID of the WireMock process.
        """
        pids = {}
        if os.path.exists(PID_TRACK_FILE):
            with open(PID_TRACK_FILE, 'r') as f:
                pids = json.load(f)
        pids[str(port)] = pid
        with open(PID_TRACK_FILE, 'w') as f:
            json.dump(pids, f)

    def _remove_pid(self, port: str | int) -> None:
        """
        Removes the PID of a WireMock instance from the tracking file.

        Args:
            port: The port of the WireMock instance to remove.
        """
        if not os.path.exists(PID_TRACK_FILE):
            return
        with open(PID_TRACK_FILE, 'r') as f:
            pids = json.load(f)
        if str(port) in pids:
            del pids[str(port)]
        with open(PID_TRACK_FILE, 'w') as f:
            json.dump(pids, f)

    def _get_pids(self) -> dict[str, int]:
        """
        Retrieves the PIDs of all tracked WireMock instances.

        Returns:
            A dictionary mapping port numbers to PIDs.
        """
        if not os.path.exists(PID_TRACK_FILE):
            return {}
        with open(PID_TRACK_FILE, 'r') as f:
            return json.load(f)

    def _cleanup_dead_pids(self) -> dict[str, int]:
        """
        Removes dead PIDs from the tracking file.

        Returns:
            A dictionary of the remaining running process PIDs.
        """
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

    def _stream_logs(self, port: str | int, pipe) -> None:
        """
        Streams the output of a WireMock instance to a log file.

        Args:
            port: The port of the WireMock instance.
            pipe: The stdout pipe of the WireMock process.
        """
        log_file_path = f'wiremock_instances/{port}/wiremock.log'
        os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
        with open(log_file_path, 'a') as f:
            for line in iter(pipe.readline, b''):
                decoded_line = line.decode().strip()
                f.write(decoded_line + '\n')
                f.flush()

    def start_wiremock(self, port: int) -> tuple[bool, str]:
        """
        Starts a new WireMock instance on the specified port.

        Args:
            port: The port number to start WireMock on.

        Returns:
            A tuple containing a boolean indicating success and a message.
        """
        port_str = str(port)
        if port_str in self.processes and self.processes[port_str].poll() is None:
            return False, f"WireMock is already running on port {port}."

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

            threading.Thread(target=self._stream_logs, args=(port_str, process.stdout), daemon=True).start()
            return True, f"Started Wiremock on port {port}."
        except Exception as e:
            return False, f"Failed to start Wiremock on port {port}: {e}"

    def stop_wiremock(self, port: int) -> tuple[bool, str]:
        """
        Stops the WireMock instance on the specified port.

        Args:
            port: The port number of the WireMock instance to stop.

        Returns:
            A tuple containing a boolean indicating success and a message.
        """
        port_str = str(port)
        process = self.processes.get(port_str)
        if not process:
            return False, "No running instance found for this port."

        try:
            parent = psutil.Process(process.pid)
            children = parent.children(recursive=True)
            for child in children:
                child.kill()
            parent.kill()
            parent.wait(5)
        except psutil.NoSuchProcess:
            # Process already killed.
            pass
        except Exception as e:
            return False, f"Error stopping WireMock on port {port}: {e}"

        self._remove_pid(port_str)
        if port_str in self.processes:
            del self.processes[port_str]
        return True, f"Stopped WireMock on port {port}."

    def is_running(self, port: int) -> bool:
        """
        Checks if a WireMock instance is currently running on the specified port.

        Args:
            port: The port to check.

        Returns:
            True if an instance is running, False otherwise.
        """
        port_str = str(port)
        process = self.processes.get(port_str)
        if not process:
            return False

        if isinstance(process, subprocess.Popen):
            return process.poll() is None
        elif isinstance(process, psutil.Process):
            return process.is_running()
        return False

    def restore_processes_on_startup(self) -> None:
        """
        Restores the state of running WireMock processes on application startup.
        """
        pids = self._cleanup_dead_pids()
        for port, pid in pids.items():
            try:
                proc = psutil.Process(pid)
                self.processes[port] = proc
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                self._remove_pid(port)

    def get_log_output(self, port: int) -> str:
        """
        Retrieves the log output for a WireMock instance from its log file.

        Args:
            port: The port of the WireMock instance.

        Returns:
            The log output as a string, or an error message if the file doesn't exist.
        """
        port_str = str(port)
        log_file_path = f'wiremock_instances/{port_str}/wiremock.log'
        if os.path.exists(log_file_path):
            with open(log_file_path, 'r') as f:
                return f.read()
        return f"Log file not found for port {port_str}."
