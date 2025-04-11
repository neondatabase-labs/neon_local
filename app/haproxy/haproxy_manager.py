import os
import json
import subprocess
from app.process_manager import ProcessManager
from app.neon import NeonAPI

class HAProxyManager(ProcessManager):
    def __init__(self):
        super().__init__()
        self.haproxy_process = None
        self.neon_api = NeonAPI()

    def prepare_config(self):
        state = self._get_neon_branch()
        current_branch = self._get_git_branch()
        parent = os.getenv("PARENT_BRANCH_ID")
        params, updated_state = self.neon_api.fetch_or_create_branch(state, current_branch, parent)
        self._write_haproxy_config(params)
        self._write_neon_branch(updated_state)

    def start_process(self):
        self.prepare_config()
        with open("/var/log/haproxy.log", "a") as log:
            self.haproxy_process = subprocess.Popen([
                "haproxy", "-f", "/tmp/haproxy.cfg"
            ], stdout=log, stderr=log)

    def stop_process(self):
        if self.haproxy_process:
            print("Stopping HAProxy...")
            self.haproxy_process.terminate()
            try:
                self.haproxy_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.haproxy_process.kill()
                self.haproxy_process.wait()
            self.haproxy_process = None

    def _write_haproxy_config(self, params):
        template_path = "/scripts/app/haproxy.cfg.tmpl"
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"HAProxy config template not found at: {template_path}")

        with open(template_path, "r") as file:
            haproxy_template = file.read()

        print(f"Params: {params}")
        haproxy_config = haproxy_template.format(**params)

        with open("/tmp/haproxy.cfg", "w") as file:
            file.write(haproxy_config)
