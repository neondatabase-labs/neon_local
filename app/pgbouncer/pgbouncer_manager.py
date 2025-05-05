import os
import json
import subprocess
from app.process_manager import ProcessManager
from app.neon import NeonAPI

class PgBouncerManager(ProcessManager):
    def __init__(self):
        super().__init__()
        self.pgbouncer_process = None
        self.neon_api = NeonAPI()

    def prepare_config(self):
        if self.parent_branch_id:
            state = self._get_neon_branch()
            current_branch = self._get_git_branch()
            parent = os.getenv("PARENT_BRANCH_ID")
            if parent == "":
                parent = None
            params, updated_state = self.neon_api.fetch_or_create_branch(state, current_branch, parent)
            self._write_neon_branch(updated_state)
        elif self.branch_id:
            params = self.neon_api.get_branch_connection_info(self.project_id, self.branch_id)
            
        self._write_pgbouncer_config(params)

    def start_process(self):
        self.prepare_config()
        with open("/var/log/pgbouncer.log", "a") as log:
            self.pgbouncer_process = subprocess.Popen([
                "/usr/bin/pgbouncer", "/etc/pgbouncer/pgbouncer.ini"
            ], stdout=log, stderr=log)

    def stop_process(self):
        if self.pgbouncer_process:
            print("Stopping PgBouncer...")
            self.pgbouncer_process.terminate()
            try:
                self.pgbouncer_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.pgbouncer_process.kill()
                self.pgbouncer_process.wait()
            self.pgbouncer_process = None
    
    def _write_pgbouncer_config(self, params):
        with open("/scripts/app/pgbouncer.ini.tmpl", "r") as file:
            template = file.read()
        config = template.format(**params)
        with open("/etc/pgbouncer/pgbouncer.ini", "w") as file:
            file.write(config)