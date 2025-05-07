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
        
        # Get and validate required environment variables
        self.project_id = os.getenv("NEON_PROJECT_ID")
        if not self.project_id:
            raise ValueError("NEON_PROJECT_ID environment variable is required")
            
        self.branch_id = os.getenv("BRANCH_ID")
            
        self.parent_branch_id = os.getenv("PARENT_BRANCH_ID")
            
        self.delete_branch = os.getenv("DELETE_BRANCH", "true").lower() == "true"
        self.vscode = os.getenv("VSCODE", "").lower() == "true"
        
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
        if not self.delete_branch:
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
        try:
            os.makedirs("/tmp/.neon_local", exist_ok=True)
            # Ensure state is properly formatted for each branch
            for branch, data in state.items():
                if isinstance(data, dict) and "branch_id" in data:
                    # Keep the existing branch_id structure
                    continue
                elif isinstance(data, list):
                    # Convert list of connection info to proper state format
                    if data and isinstance(data[0], dict) and "database" in data[0]:
                        # Extract branch_id from the first connection info
                        branch_id = data[0].get("branch_id")
                        if branch_id:
                            state[branch] = {"branch_id": branch_id}
            with open("/tmp/.neon_local/.branches", "w") as file:
                json.dump(state, file)
        except Exception as e:
            print(f"Failed to write state file: {str(e)}")

    def start_process(self):
        raise NotImplementedError

    def stop_process(self):
        raise NotImplementedError

    def reload(self):
        self.stop_process()
        self.start_process()

    def cleanup(self):
        if self.delete_branch:
            self.branch_cleanup()
        self.shutdown_event.set()
        with self.config_cv:
            self.config_cv.notify_all()
        if self.watcher_thread:
            self.watcher_thread.join()
        if self.reloader_thread:
            self.reloader_thread.join()
        print("Cleanup complete.")
