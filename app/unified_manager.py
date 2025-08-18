import os
import json
import subprocess
import threading
import time
import socket
import requests
from app.process_manager import ProcessManager
from app.neon import NeonAPI

class UnifiedManager(ProcessManager):
    def __init__(self):
        super().__init__()
        self.envoy_process = None
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
        
        # Store params for use in start_process
        self.database_params = params
        
        self._write_pgbouncer_config(params)
        self._write_envoy_config(params)

    def start_process(self):
        self.prepare_config()
        
        # Update /etc/hosts with the actual database hostnames now that we have them
        if hasattr(self, 'database_params') and self.database_params:
            import socket, subprocess
            try:
                for db in self.database_params:
                    hostname = db['host']
                    # Get IPv4 addresses for the hostname
                    ipv4_info = socket.getaddrinfo(hostname, 5432, socket.AF_INET)
                    ipv4_addr = ipv4_info[0][4][0]  # Get first IPv4 address
                    
                    # Use subprocess to run as root and update /etc/hosts
                    hosts_entry = f"{ipv4_addr} {hostname}"
                    print(f"Adding to /etc/hosts: {hosts_entry}")
                    
                    # Remove existing entry and add new one
                    subprocess.run(["sudo", "sed", "-i", f"/{hostname}/d", "/etc/hosts"], check=False)
                    subprocess.run(["sudo", "sh", "-c", f"echo '{hosts_entry}' >> /etc/hosts"], check=True)
                    
                print("Successfully updated /etc/hosts with runtime database hostnames")
            except Exception as e:
                print(f"Failed to update /etc/hosts at runtime: {e}")
                
        # Start PgBouncer first (on internal port 6432)
        print("Starting PgBouncer...")
        
        # Set environment variables for Neon endpoint support
        pgbouncer_env = os.environ.copy()
        if hasattr(self, 'database_params') and self.database_params:
            # Extract endpoint ID from first database for environment variable
            endpoint_id = self.database_params[0]['host'].split('.')[0]
            pgbouncer_env['PGOPTIONS'] = f'-c endpoint={endpoint_id}'
            # Force IPv4-only DNS resolution for PgBouncer
            pgbouncer_env['RES_OPTIONS'] = 'inet inet6:off'
            pgbouncer_env['RESOLV_HOST_CONF'] = '/dev/null'
            print(f"Setting PGOPTIONS environment variable: -c endpoint={endpoint_id}")
            print(f"Forcing IPv4-only DNS resolution for PgBouncer")
        
        with open("/var/log/pgbouncer.log", "a") as log:
            self.pgbouncer_process = subprocess.Popen([
                "/usr/local/bin/pgbouncer_wrapper.sh", "/etc/pgbouncer/pgbouncer.ini"
            ], stdout=log, stderr=log, env=pgbouncer_env)
        
        # Start Envoy (on port 5432, routing to PgBouncer and Neon)
        print("Starting Envoy...")
        with open("/var/log/envoy.log", "a") as log:
            self.envoy_process = subprocess.Popen([
                "/usr/local/bin/envoy", "-c", "/tmp/envoy.yaml", "--log-level", "info"
            ], stdout=log, stderr=log)
        
        # Wait for services to be healthy before declaring ready
        self._wait_for_services_healthy()
        
        print("Neon Local is ready - Envoy and PgBouncer are both running")

    def stop_process(self):
        # Stop Envoy first
        if self.envoy_process:
            print("Stopping Envoy...")
            self.envoy_process.terminate()
            try:
                self.envoy_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.envoy_process.kill()
                self.envoy_process.wait()
            self.envoy_process = None
        
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
        import socket
        database_entries = []
        for db in databases:
            # Extract endpoint ID from hostname for Neon SNI support
            endpoint_id = db['host'].split('.')[0]
            
            # Keep hostname for SNI support
            host = db['host']
            
            entry = f"{db['database']}=user={db['user']} password={db['password']} host={host} port=5432 dbname={db['database']} application_name={app_name}"
            database_entries.append(entry)
        
        # Add wildcard entry pointing to the first database
        if databases:
            first_db = databases[0]
            endpoint_id = first_db['host'].split('.')[0]
            
            # Keep hostname for SNI support
            host = first_db['host']
            
            wildcard_entry = f"*=user={first_db['user']} password={first_db['password']} host={host} port=5432 dbname={first_db['database']} application_name={app_name}"
            database_entries.append(wildcard_entry)
        
        # Modify pgbouncer section to listen on port 6432 (internal port)
        pgbouncer_section = pgbouncer_section.replace("listen_port = 5432", "listen_port = 6432")
        
        # Combine all sections
        config = f"[databases]\n" + "\n".join(database_entries) + "\n\n[pgbouncer]\n" + pgbouncer_section
        
        with open("/etc/pgbouncer/pgbouncer.ini", "w") as file:
            file.write(config)

    def _write_envoy_config(self, databases):
        template_path = "/scripts/app/envoy/envoy.yaml.tmpl"
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"Envoy config template not found at: {template_path}")

        with open(template_path, "r") as file:
            envoy_template = file.read()

        print(f"Databases: {databases}")
        
        # Determine application name based on CLIENT environment variable
        client = os.getenv("CLIENT", "").lower()
        app_name = "neon_local_vscode_container" if client == "vscode" else "neon_local_container"
        user_agent_suffix = "_neon_local_vscode_container" if client == "vscode" else "_neon_local_container"
        
        # Define injection markers
        routes_marker = "              # Database-specific routes will be injected here"
        clusters_marker = "  # Database-specific clusters will be injected here"
        
        # Build database-specific routes
        database_routes = ""
        database_clusters = ""
        
        for db in databases:
            cluster_name = f"neon_cluster_{db['database']}"
            
            # Create routes for this database
            database_routes += f"""
              # HTTP routes for {db['database']}
              - match:
                  prefix: "/{db['database']}"
                route:
                  cluster: {cluster_name}
                  timeout: 30s
                request_headers_to_add:
                - header:
                    key: "neon-connection-string"
                    value: "postgresql://{db['user']}:{db['password']}@{db['host']}/{db['database']}?sslmode=require&application_name={app_name}"
                - header:
                    key: "user-agent"
                    value: "node{user_agent_suffix}"
              - match:
                  prefix: "/"
                  headers:
                  - name: "neon-connection-string"
                    string_match:
                      contains: "{db['database']}"
                route:
                  cluster: {cluster_name}
                  timeout: 30s
                request_headers_to_add:
                - header:
                    key: "neon-connection-string"
                    value: "postgresql://{db['user']}:{db['password']}@{db['host']}/{db['database']}?sslmode=require&application_name={app_name}"
                - header:
                    key: "user-agent"
                    value: "node{user_agent_suffix}"
              
              # WebSocket routes for {db['database']}
              - match:
                  prefix: "/{db['database']}"
                  headers:
                  - name: "upgrade"
                    string_match:
                      exact: "websocket"
                route:
                  cluster: {cluster_name}
                  timeout: 0s  # No timeout for WebSocket connections
                  upgrade_configs:
                  - upgrade_type: "websocket"
                request_headers_to_add:
                - header:
                    key: "neon-connection-string"
                    value: "postgresql://{db['user']}:{db['password']}@{db['host']}/{db['database']}?sslmode=require&application_name={app_name}"
              - match:
                  prefix: "/"
                  headers:
                  - name: "upgrade"
                    string_match:
                      exact: "websocket"
                  - name: "neon-connection-string"
                    string_match:
                      contains: "{db['database']}"
                route:
                  cluster: {cluster_name}
                  timeout: 0s  # No timeout for WebSocket connections
                  upgrade_configs:
                  - upgrade_type: "websocket"
                request_headers_to_add:
                - header:
                    key: "neon-connection-string"
                    value: "postgresql://{db['user']}:{db['password']}@{db['host']}/{db['database']}?sslmode=require&application_name={app_name}"
"""
            
            # Create cluster for this database
            database_clusters += f"""
  - name: {cluster_name}
    connect_timeout: 5s
    type: STRICT_DNS
    lb_policy: ROUND_ROBIN
    dns_lookup_family: V4_ONLY
    transport_socket:
      name: envoy.transport_sockets.tls
      typed_config:
        "@type": type.googleapis.com/envoy.extensions.transport_sockets.tls.v3.UpstreamTlsContext
        common_tls_context:
          validation_context: {{}}
    load_assignment:
      cluster_name: {cluster_name}
      endpoints:
      - lb_endpoints:
        - endpoint:
            address:
              socket_address:
                address: {db['host']}
                port_value: 443
    health_checks:
    - timeout: 5s
      interval: 3s
      interval_jitter: 1s
      unhealthy_threshold: 2
      healthy_threshold: 2
      http_health_check:
        path: "/sql"
        request_headers_to_add:
        - header:
            key: "neon-connection-string"
            value: "postgresql://{db['user']}:{db['password']}@{db['host']}/{db['database']}?sslmode=require&application_name={app_name}"

        - header:
            key: "user-agent"
            value: "envoy-health-check{user_agent_suffix}"
        - header:
            key: "content-type"
            value: "application/json"

"""
        
        # Update default cluster reference if we have databases
        if databases:
            first_db = databases[0]
            default_cluster_replacement = f"neon_cluster_{first_db['database']}"
            envoy_template = envoy_template.replace("neon_cluster_default", default_cluster_replacement)
            
            # Replace placeholder connection string with actual connection string for default routes
            default_connection_string = f"postgresql://{first_db['user']}:{first_db['password']}@{first_db['host']}/{first_db['database']}?sslmode=require&application_name={app_name}"
            envoy_template = envoy_template.replace("PLACEHOLDER_NEON_CONNECTION_STRING", default_connection_string)
            
            # Replace placeholder user agent
            default_user_agent = f"node{user_agent_suffix}"
            envoy_template = envoy_template.replace("PLACEHOLDER_USER_AGENT", default_user_agent)
            
            # Replace placeholder neon host for Lua filter
            default_neon_host = first_db['host']
            envoy_template = envoy_template.replace("PLACEHOLDER_NEON_HOST", default_neon_host)
            
            # Replace placeholder connection string for Lua filter body modification
            lua_connection_string = f"postgresql://{first_db['user']}:{first_db['password']}@{first_db['host']}/{first_db['database']}?sslmode=require&application_name={app_name}"
            envoy_template = envoy_template.replace("PLACEHOLDER_NEON_CONNECTION_STRING", lua_connection_string)
            

        
        # Inject configurations into template
        envoy_config = envoy_template.replace(routes_marker, database_routes)
        envoy_config = envoy_config.replace(clusters_marker, database_clusters)

        with open("/tmp/envoy.yaml", "w") as file:
            file.write(envoy_config)

    def _is_port_open(self, host, port, timeout=1):
        """Check if a port is open and accepting connections."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except Exception:
            return False

    def _check_pgbouncer_health(self):
        """Check if PgBouncer is healthy and accepting connections."""
        # PgBouncer runs on internal port 6432
        return self._is_port_open('127.0.0.1', 6432)

    def _check_envoy_health(self):
        """Check if Envoy is healthy and accepting connections."""
        # Envoy runs on port 5432
        if not self._is_port_open('127.0.0.1', 5432):
            return False
        
        # Additional check: try a simple HTTP request to ensure HTTP backend is working
        try:
            response = requests.get('http://127.0.0.1:5432', timeout=2)
            # We expect this to fail with a specific error, but it should connect
            return True
        except requests.exceptions.ConnectionError:
            # If connection is refused, Envoy is not ready
            return False
        except Exception:
            # Other exceptions (like HTTP errors) are fine - it means Envoy is responding
            return True

    def _wait_for_services_healthy(self, max_wait_time=30, check_interval=0.5):
        """Wait for both PgBouncer and Envoy to be healthy before proceeding."""
        print("Waiting for services to be healthy...")
        
        start_time = time.time()
        pgbouncer_ready = False
        envoy_ready = False
        
        while time.time() - start_time < max_wait_time:
            if not pgbouncer_ready:
                pgbouncer_ready = self._check_pgbouncer_health()
                if pgbouncer_ready:
                    print("✓ PgBouncer is healthy")
            
            if not envoy_ready:
                envoy_ready = self._check_envoy_health()
                if envoy_ready:
                    print("✓ Envoy is healthy")
            
            if pgbouncer_ready and envoy_ready:
                print("✓ All services are healthy and ready for traffic")
                return True
            
            time.sleep(check_interval)
        
        # If we get here, services didn't become healthy in time
        pgbouncer_status = "✓" if pgbouncer_ready else "✗"
        envoy_status = "✓" if envoy_ready else "✗"
        
        print(f"⚠️  Health check timeout after {max_wait_time}s:")
        print(f"   PgBouncer (port 6432): {pgbouncer_status}")
        print(f"   Envoy (port 5432): {envoy_status}")
        print("Services may not be fully ready for traffic")
        
        return False