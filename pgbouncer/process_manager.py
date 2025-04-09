
import threading
import hashlib
import time
import os
import json
import requests

API_URL = "https://console.neon.tech/api/v2"

class ProcessManager:
    def __init__(self):
        self.shutdown_event = threading.Event()
        self.config_cv = threading.Condition()
        self.reload_lock = threading.Lock()
        self.reload_needed = False
        self.watcher_thread = None
        self.reloader_thread = None

    def calculate_file_hash(self, path):
        if not os.path.exists(path):
            return None
        with open(path, "rb") as file:
            return hashlib.sha256(file.read()).hexdigest()

    def watch_file_changes(self, file_path):
        last_hash = self.calculate_file_hash(file_path)
        print(f"Watching {file_path} for changes...")
        while not self.shutdown_event.is_set():
            time.sleep(1)
            try:
                current_hash = self.calculate_file_hash(file_path)
                if current_hash != last_hash:
                    print("File changed. Triggering reload...")
                    last_hash = current_hash
                    with self.reload_lock:
                        self.reload_needed = True
                    with self.config_cv:
                        self.config_cv.notify()
            except Exception as e:
                print(f"Error watching file: {e}")

    def start_reloader_loop(self):
        self.start_process()
        while not self.shutdown_event.is_set():
            with self.config_cv:
                self.config_cv.wait(timeout=1)
                if self.shutdown_event.is_set():
                    break
                with self.reload_lock:
                    if not self.reload_needed:
                        continue
                    self.reload_needed = False
            print("Reload triggered.")
            self.reload()
        self.stop_process()

    def branch_cleanup(self):
        print("Running branch cleanup...")
        try:
            with open("/scripts/.neon_local/.branches", "r") as file:
                state = json.load(file)
        except:
            print("No state file found.")
            state = {}

        current_branch = self._get_git_branch()
        if not current_branch:
            print("No current branch found.")
            return

        api_key = os.getenv("NEON_API_KEY")
        project_id = os.getenv("NEON_PROJECT_ID")
        if not api_key or not project_id:
            print("No NEON_API_KEY or NEON_PROJECT_ID set, skipping Neon cleanup.")
            return

        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        params = state.get(current_branch)
        if params:
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

    def _get_git_branch(self):
        try:
            with open("/scripts/.git/HEAD", "r") as file:
                return file.read().split(":", 1)[1].split("/", 2)[-1].strip()
        except:
            return None

    def start_process(self):
        raise NotImplementedError

    def stop_process(self):
        raise NotImplementedError

    def reload(self):
        self.stop_process()
        self.start_process()

    def cleanup(self):
        self.branch_cleanup()
        self.shutdown_event.set()
        with self.config_cv:
            self.config_cv.notify_all()
        if self.watcher_thread:
            self.watcher_thread.join()
        if self.reloader_thread:
            self.reloader_thread.join()
        print("Cleanup complete.")
