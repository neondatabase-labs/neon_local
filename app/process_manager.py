import threading
import hashlib
import time
import os
import json
from app.neon import NeonAPI

class ProcessManager:
    def __init__(self):
        self.shutdown_event = threading.Event()
        self.config_cv = threading.Condition()
        self.reload_lock = threading.Lock()
        self.reload_needed = False
        self.watcher_thread = None
        self.reloader_thread = None
        self.neon = NeonAPI()
        self.project_id = os.getenv("NEON_PROJECT_ID")
        self.branch_id = os.getenv("BRANCH_ID")
        # Treat empty string the same as None
        if self.branch_id == "":
            self.branch_id = None
        self.manage_branches = self.project_id is None or self.branch_id is None

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
        if not self.manage_branches:
            return
            
        print("Running branch cleanup...")
        state = self._get_neon_branch()
        print("State")
        print(state)
        current_branch = self._get_git_branch()
        print(current_branch)
        print("current_branch")
        state = self.neon.cleanup_branch(state, current_branch)
        print("state")
        print(state)
        self._write_neon_branch(state)

    def _get_git_branch(self):
        try:
            with open("/tmp/.git/HEAD", "r") as file:
                return file.read().split(":", 1)[1].split("/", 2)[-1].strip()
        except:
            return None
        
    def _get_neon_branch(self):
        try:
            with open("/tmp/.neon_local/.branches", "r") as file:
                return json.load(file)
        except:
            print("No state file found.")
            return {}

    def _write_neon_branch(self, state):
        if not self.manage_branches:
            return
            
        try:
            os.makedirs("/tmp/.neon_local", exist_ok=True)
            with open("/tmp/.neon_local/.branches", "w") as file:
                json.dump(state, file)
        except:
            print("Failed to write state file.")

    def start_process(self):
        raise NotImplementedError

    def stop_process(self):
        raise NotImplementedError

    def reload(self):
        self.stop_process()
        self.start_process()

    def cleanup(self):
        delete_branch = os.getenv("DELETE_BRANCH", "true").lower() == "true" and self.manage_branches
        if delete_branch:
            self.branch_cleanup()
        self.shutdown_event.set()
        with self.config_cv:
            self.config_cv.notify_all()
        if self.watcher_thread:
            self.watcher_thread.join()
        if self.reloader_thread:
            self.reloader_thread.join()
        print("Cleanup complete.")
