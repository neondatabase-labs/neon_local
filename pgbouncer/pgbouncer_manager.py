
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

        params, updated_state = self.neon_api.fetch_or_create_branch(state, current_branch)

        with open("/scripts/app/pgbouncer.ini.tmpl", "r") as file:
            template = file.read()

        config = template.format(**params)
        with open("/etc/pgbouncer/pgbouncer.ini", "w") as file:
            file.write(config)

        try:
            with open("/scripts/.neon_local/.branches", "w") as file:
                json.dump(updated_state, file)
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
