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
        params = None
        print(f"Debug: parent_branch_id={self.parent_branch_id}, branch_id={self.branch_id}")
        
        if self.parent_branch_id:
            print("Debug: Using parent branch flow")
            state = self._get_neon_branch()
            current_branch = self._get_git_branch()
            parent = os.getenv("PARENT_BRANCH_ID")
            if parent == "":
                parent = None
            print(f"Debug: current_branch={current_branch}, parent={parent}")
            params, updated_state = self.neon_api.fetch_or_create_branch(state, current_branch, parent, self.vscode)
            self._write_neon_branch(updated_state)
        elif self.branch_id:
            print(f"Debug: Using direct branch flow with branch_id={self.branch_id}")
            try:
                params = self.neon_api.get_branch_connection_info(self.project_id, self.branch_id)
                print(f"Debug: Got connection info: {params}")
            except Exception as e:
                print(f"Debug: Error getting connection info: {str(e)}")
                raise
        else:
            print("Debug: No branch ID provided, creating new branch from main")
            state = self._get_neon_branch()
            current_branch = self._get_git_branch()
            params, updated_state = self.neon_api.fetch_or_create_branch(state, current_branch, vscode=self.vscode)
            self._write_neon_branch(updated_state)
        
        if params is None:
            print("Debug: No parameters obtained from any flow")
            raise ValueError("Failed to get connection parameters")
            
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
    
    def _write_pgbouncer_config(self, databases):
        with open("/scripts/app/pgbouncer.ini.tmpl", "r") as file:
            template = file.read()
        
        # Split the template into sections
        sections = template.split("[pgbouncer]")
        databases_section = sections[0].strip()
        pgbouncer_section = sections[1].strip()
        
        # Generate database entries for each database
        database_entries = []
        for db in databases:
            entry = f"{db['database']}=user={db['user']} password={db['password']} host={db['host']} port=5432 dbname={db['database']}"
            database_entries.append(entry)
        
        # Add wildcard entry pointing to the first database
        if databases:
            first_db = databases[0]
            wildcard_entry = f"*=user={first_db['user']} password={first_db['password']} host={first_db['host']} port=5432 dbname={first_db['database']}"
            database_entries.append(wildcard_entry)
        
        # Combine all sections
        config = f"[databases]\n" + "\n".join(database_entries) + "\n\n[pgbouncer]\n" + pgbouncer_section
        
        with open("/etc/pgbouncer/pgbouncer.ini", "w") as file:
            file.write(config)