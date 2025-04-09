
import os
import json
import subprocess
import requests
from app.process_manager import ProcessManager

class PgBouncerManager(ProcessManager):
    def __init__(self):
        super().__init__()
        self.pgbouncer_process = None

    def prepare_config(self):
        api_key = os.getenv("NEON_API_KEY")
        project_id = os.getenv("NEON_PROJECT_ID")
        if not api_key or not project_id:
            raise ValueError("NEON_API_KEY or NEON_PROJECT_ID not set.")

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

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        params = state.get(current_branch) if current_branch else None
        if params:
            try:
                requests.get(f"https://console.neon.tech/api/v2/projects/{project_id}/branches/{params['branch_id']}", headers=headers).raise_for_status()
            except:
                print("No branch found at Neon.")
                params = None

        if params is None:
            payload = {"endpoints": [{"type": "read_write"}]}
            response = requests.post(f"https://console.neon.tech/api/v2/projects/{project_id}/branches", headers=headers, json=payload)
            response.raise_for_status()
            json_response = response.json()
            params = json_response["connection_uris"][0]["connection_parameters"]
            params["branch_id"] = json_response["branch"]["id"]
            if current_branch:
                state[current_branch] = params

        with open("/scripts/app/pgbouncer.ini.tmpl", "r") as file:
            template = file.read()

        config = template.format(**params)
        with open("/etc/pgbouncer/pgbouncer.ini", "w") as file:
            file.write(config)

        try:
            with open("/scripts/.neon_local/.branches", "w") as file:
                json.dump(state, file)
        except:
            print("Failed to write state file.")

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
