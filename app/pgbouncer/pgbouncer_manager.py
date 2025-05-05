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
        self.cert_path = "/etc/pgbouncer/server.crt"
        self.key_path = "/etc/pgbouncer/server.key"

    def _generate_certificates(self):
        """Generate self-signed certificates if they don't exist."""
        if os.path.exists(self.cert_path) and os.path.exists(self.key_path):
            return

        print("Generating self-signed certificates...")
        # Generate private key
        subprocess.run([
            "openssl", "genrsa", "-out", self.key_path, "2048"
        ], check=True)
        
        # Generate CSR
        subprocess.run([
            "openssl", "req", "-new", "-key", self.key_path,
            "-out", "/tmp/server.csr",
            "-subj", "/CN=localhost"
        ], check=True)
        
        # Generate self-signed certificate
        subprocess.run([
            "openssl", "x509", "-req", "-days", "365",
            "-in", "/tmp/server.csr",
            "-signkey", self.key_path,
            "-out", self.cert_path
        ], check=True)
        
        # Set proper permissions
        os.chmod(self.key_path, 0o600)
        os.chmod(self.cert_path, 0o644)
        
        # Clean up CSR
        os.remove("/tmp/server.csr")

    def prepare_config(self):
        self._generate_certificates()
        state = self._get_neon_branch()
        current_branch = self._get_git_branch()
        parent = os.getenv("PARENT_BRANCH_ID")
        params, updated_state = self.neon_api.fetch_or_create_branch(state, current_branch, parent)
        self._write_pgbouncer_config(params)
        self._write_neon_branch(updated_state)

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