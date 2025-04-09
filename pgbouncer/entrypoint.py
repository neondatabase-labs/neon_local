import json
import hashlib
import os
import time
import subprocess
import threading
import requests
import signal
import sys

API_URL = "https://console.neon.tech/api/v2"


class PgBouncerManager:
    def __init__(self):
        self.pgbouncer_process: subprocess.Popen | None = None
        self.watcher_thread: threading.Thread | None = None
        self.shutdown_event = threading.Event()
        self.config_cv = threading.Condition()
        self.reload_needed = False
        self.reload_lock = threading.Lock()

    def calculate_file_hash(self, path):
        with open(path, "rb") as file:
            return hashlib.sha256(file.read()).hexdigest()

    def watch_file_changes(self, file_path="/scripts/.git/HEAD"):
        last_hash = self.calculate_file_hash(file_path)
        print("Watching for file changes...")
        while not self.shutdown_event.is_set():
            time.sleep(1)
            try:
                current_hash = self.calculate_file_hash(file_path)
                if current_hash != last_hash:
                    print("File changed. Notifying PgBouncer reload.")
                    last_hash = current_hash
                    with self.reload_lock:
                        self.reload_needed = True
                    with self.config_cv:
                        self.config_cv.notify()
            except Exception as e:
                print(f"Error watching file: {e}")

    def prepare_config(self) -> None:
        api_key = os.getenv("NEON_API_KEY")
        project_id = os.getenv("NEON_PROJECT_ID")
        if not api_key or not project_id:
            raise ValueError("NEON_API_KEY or NEON_PROJECT_ID not set in environment variables.")

        try:
            with open("/scripts/.neon_local/.branches", "r") as file:
                state = json.load(file)
        except:
            print("No state file found.")
            state = {}

        try:
            with open("/scripts/.git/HEAD", "r") as file:
                current_branch = file.read().split(":", 1)[1].split("/", 2)[-1].strip()
        except:
            print("No branch found from git file.")
            current_branch = None

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        params = None
        if current_branch and (params := state.get(current_branch)) is not None:
            try:
                requests.get(f"{API_URL}/projects/{project_id}/branches/{params['branch_id']}", headers=headers).raise_for_status()
            except:
                print("No branch found at Neon.")
                params = None

        if params is None:
            payload = {"endpoints": [{"type": "read_write"}]}
            response = requests.post(f"{API_URL}/projects/{project_id}/branches", headers=headers, json=payload)
            response.raise_for_status()
            json_response = response.json()
            params = json_response["connection_uris"][0]["connection_parameters"]
            params["branch_id"] = json_response["branch"]["id"]
            if current_branch:
                state[current_branch] = params

        with open("/scripts/pgbouncer.ini.tmpl", "r") as file:
            pgbouncer_template = file.read()

        pgbouncer_config = pgbouncer_template.format(**params)

        with open("/etc/pgbouncer/pgbouncer.ini", "w") as file:
            file.write(pgbouncer_config)

        try:
            with open("/scripts/.neon_local/.branches", "w") as file:
                json.dump(state, file)
        except:
            print("Failed to write state file.")

    def start_pgbouncer(self):
        self.prepare_config()
        log_file = "/var/log/pgbouncer.log"
        with open(log_file, "a") as log:
            self.pgbouncer_process = subprocess.Popen([
                "/usr/bin/pgbouncer", "/etc/pgbouncer/pgbouncer.ini"
            ], stdout=log, stderr=log)

    def stop_pgbouncer(self):
        if self.pgbouncer_process:
            print("Stopping PgBouncer...")
            self.pgbouncer_process.terminate()
            try:
                self.pgbouncer_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print("PgBouncer didn't stop in time. Killing.")
                self.pgbouncer_process.kill()
                self.pgbouncer_process.wait()
            self.pgbouncer_process = None

    def pgbouncer_reloader(self):
        self.start_pgbouncer()
        while not self.shutdown_event.is_set():
            with self.config_cv:
                self.config_cv.wait(timeout=1)
                if self.shutdown_event.is_set():
                    break
                with self.reload_lock:
                    if not self.reload_needed:
                        continue
                    self.reload_needed = False
            print("Reloading PgBouncer...")
            self.stop_pgbouncer()
            self.start_pgbouncer()
        self.stop_pgbouncer()


def branch_cleanup():
    try:
        with open("/scripts/.neon_local/.branches", "r") as file:
            state = json.load(file)
    except:
        print("No state file found.")
        state = {}

    try:
        with open("/scripts/.git/HEAD", "r") as file:
            current_branch = file.read().split(":", 1)[1].split("/", 2)[-1].strip()
    except:
        print("No branch found.")
        current_branch = None

    api_key = os.getenv("NEON_API_KEY")
    project_id = os.getenv("NEON_PROJECT_ID")
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    
    params = state.get(current_branch)
    if current_branch and params:
        try:
            requests.get(f"{API_URL}/projects/{project_id}/branches/{params['branch_id']}", headers=headers).raise_for_status()
        except:
            print("Branch not found at Neon.")
            params = None

        if params:
            response = requests.delete(f"{API_URL}/projects/{project_id}/branches/{params['branch_id']}", headers=headers)
            print(response)
            response.raise_for_status()
            print(response.json())

    if current_branch in state:
        print(f"Removing branch state: {state.pop(current_branch)}")

    try:
        with open("/scripts/.neon_local/.branches", "w") as file:
            json.dump(state, file)
            print(f"Updated state: {state}")
    except:
        print("Failed to save updated state.")


def cleanup(manager):
    print("Performing cleanup...")
    branch_cleanup()
    manager.shutdown_event.set()
    with manager.config_cv:
        manager.config_cv.notify_all()
    if manager.watcher_thread:
        manager.watcher_thread.join()
    print("Cleanup complete.")


def main():
    print("main")
    manager = PgBouncerManager()

    def handle_signal(signum, frame):
        print("handle signal")
        print(f"Received signal {signum}, shutting down...")
        cleanup(manager)
        sys.exit(0)

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    reloader_thread = threading.Thread(target=manager.pgbouncer_reloader)
    manager.watcher_thread = threading.Thread(target=manager.watch_file_changes)

    reloader_thread.start()
    manager.watcher_thread.start()

    reloader_thread.join()


if __name__ == "__main__":
    main()

