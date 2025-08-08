import os
import json
import subprocess
import threading
from app.process_manager import ProcessManager
from app.neon import NeonAPI

class UnifiedManager(ProcessManager):
    def __init__(self):
        super().__init__()
        self.haproxy_process = None
        self.pgbouncer_process = None
        self.neon_api = NeonAPI()
        self.cert_path = "/etc/pgbouncer/server.crt"
        self.key_path = "/etc/pgbouncer/server.key"

    def _generate_certificates(self):
        """Generate self-signed certificates if they don't exist."""
        if os.path.exists(self.cert_path) and os.path.exists(self.key_path):
            return

        print("Generating self-signed certificate...")
        # Ensure directory exists
        os.makedirs("/etc/pgbouncer", exist_ok=True)
        
        # Generate private key
        subprocess.run([
            "openssl", "genrsa", "-out", self.key_path, "2048"
        ], check=True, capture_output=True)
        
        # Generate CSR
        subprocess.run([
            "openssl", "req", "-new", "-key", self.key_path,
            "-out", "/tmp/server.csr",
            "-subj", "/CN=localhost/O=DO NOT TRUST/OU=Neon Local self-signed cert"
        ], check=True, capture_output=True)
        
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
        params = None
        
        if self.branch_id:
            try:
                params = self.neon_api.get_branch_connection_info(self.project_id, self.branch_id)
            except Exception as e:
                print(f"Debug: Error getting connection info: {str(e)}")
                raise
        elif self.parent_branch_id:
            state = self._get_neon_branch()
            current_branch = self._get_git_branch()
            parent = os.getenv("PARENT_BRANCH_ID")
            if parent == "":
                parent = None
            params, updated_state = self.neon_api.fetch_or_create_branch(state, current_branch, parent, self.vscode)
            self._write_neon_branch(updated_state)

        else:
            state = self._get_neon_branch()
            current_branch = self._get_git_branch()
            params, updated_state = self.neon_api.fetch_or_create_branch(state, current_branch, vscode=self.vscode)
            self._write_neon_branch(updated_state)
        
        if params is None:
            raise ValueError("Failed to get connection parameters")
            
        self._write_pgbouncer_config(params)
        self._write_haproxy_config(params)

    def start_process(self):
        self.prepare_config()
        
        # Start PgBouncer first (on internal port 6432)
        print("Starting PgBouncer...")
        with open("/var/log/pgbouncer.log", "a") as log:
            self.pgbouncer_process = subprocess.Popen([
                "/usr/bin/pgbouncer", "/etc/pgbouncer/pgbouncer.ini"
            ], stdout=log, stderr=log)
        
        # Start HAProxy (on port 5432, routing to PgBouncer and Neon)
        print("Starting HAProxy...")
        with open("/var/log/haproxy.log", "a") as log:
            self.haproxy_process = subprocess.Popen([
                "haproxy", "-f", "/tmp/haproxy.cfg"
            ], stdout=log, stderr=log)
        
        print("Neon Local is ready - HAProxy and PgBouncer are both running")

    def stop_process(self):
        # Stop HAProxy first
        if self.haproxy_process:
            print("Stopping HAProxy...")
            self.haproxy_process.terminate()
            try:
                self.haproxy_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.haproxy_process.kill()
                self.haproxy_process.wait()
            self.haproxy_process = None
        
        # Then stop PgBouncer
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
        
        # Determine application name based on CLIENT environment variable
        client = os.getenv("CLIENT", "").lower()
        app_name = "neon_local_vscode_container" if client == "vscode" else "neon_local_container"
        
        # Generate database entries for each database
        database_entries = []
        for db in databases:
            entry = f"{db['database']}=user={db['user']} password={db['password']} host={db['host']} port=5432 dbname={db['database']} application_name={app_name}"
            database_entries.append(entry)
        
        # Add wildcard entry pointing to the first database
        if databases:
            first_db = databases[0]
            wildcard_entry = f"*=user={first_db['user']} password={first_db['password']} host={first_db['host']} port=5432 dbname={first_db['database']} application_name={app_name}"
            database_entries.append(wildcard_entry)
        
        # Modify pgbouncer section to listen on port 6432 (internal port)
        pgbouncer_section = pgbouncer_section.replace("listen_port = 5432", "listen_port = 6432")
        
        # Combine all sections
        config = f"[databases]\n" + "\n".join(database_entries) + "\n\n[pgbouncer]\n" + pgbouncer_section
        
        with open("/etc/pgbouncer/pgbouncer.ini", "w") as file:
            file.write(config)

    def _write_haproxy_config(self, databases):
        template_path = "/scripts/app/haproxy.cfg.tmpl"
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"HAProxy config template not found at: {template_path}")

        with open(template_path, "r") as file:
            haproxy_template = file.read()

        print(f"Databases: {databases}")
        
        # Determine application name and user agent suffix based on CLIENT environment variable
        client = os.getenv("CLIENT", "").lower()
        app_name = "neon_local_vscode_container" if client == "vscode" else "neon_local_container"
        user_agent_suffix = "_neon_local_vscode_container" if client == "vscode" else "_neon_local_container"
        
        # Split the template to add HTTP backend configuration
        sections = haproxy_template.split("# Backend selection rules will be added here")
        frontend_section = sections[0].strip()
        
        # Generate HTTP backend configuration for each database
        http_backend_config = ""
        for db in databases:
            http_backend_config += f"""    server ws_server_{db['database']} {db['host']}:443 ssl verify none sni str({db['host']}) check
    http-request set-header Neon-Connection-String "postgresql://{db['user']}:{db['password']}@{db['host']}/{db['database']}?sslmode=require&application_name={app_name}"
    http-request set-header Host {db['host']}
    http-request set-header User-Agent "%[req.hdr(User-Agent)]{user_agent_suffix}"
"""
            break  # Use first database for HTTP backend

        # Combine the configuration
        haproxy_config = frontend_section + "\n" + http_backend_config

        with open("/tmp/haproxy.cfg", "w") as file:
            file.write(haproxy_config)