import os
import json
import subprocess
import threading
import time
import socket
import signal
import requests
import logging
from app.process_manager import ProcessManager
from app.neon import NeonAPI

class UnifiedManager(ProcessManager):
    def __init__(self):
        super().__init__()
        self.envoy_process = None
        self.pgbouncer_process = None
        self.wsproxy_process = None
        self.neon_api = NeonAPI()
        self.cert_path = "/etc/pgbouncer/server.crt"
        self.key_path = "/etc/pgbouncer/server.key"
        self.connection_monitor_thread = None
        self.monitoring_enabled = True
        self.recovery_thread = None
        self.recovery_enabled = True
        self.pgbouncer_restart_count = 0
        self.max_pgbouncer_restarts = 5
        self.last_pgbouncer_restart = 0
        self.restart_cooldown = 60  # 60 seconds between restarts
        self.last_log_check_time = 0  # Track last log analysis time
        self.pgbouncer_start_time = 0  # Track when PgBouncer was started

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
        
        # Track when PgBouncer was started for log analysis
        self.pgbouncer_start_time = time.time()
        
        # Start WebSocket proxy (on port 8080, routing WebSocket traffic to PgBouncer)
        print("Starting WebSocket proxy...")
        wsproxy_env = os.environ.copy()
        wsproxy_env['WSPROXY_PORT'] = '8080'
        wsproxy_env['PGBOUNCER_HOST'] = '127.0.0.1'
        wsproxy_env['PGBOUNCER_PORT'] = '6432'
        
        with open("/var/log/wsproxy.log", "a") as log:
            self.wsproxy_process = subprocess.Popen([
                "python3", "/scripts/app/wsproxy/neon_wsproxy_manager.py"
            ], stdout=log, stderr=log, env=wsproxy_env)
        
        # Start Envoy (on port 5432, routing to PgBouncer and Neon)
        print("Starting Envoy...")
        with open("/var/log/envoy.log", "a") as log:
            self.envoy_process = subprocess.Popen([
                "/usr/local/bin/envoy", "-c", "/tmp/envoy.yaml", "--log-level", "info"
            ], stdout=log, stderr=log)
        
        # Wait for services to be healthy before declaring ready
        self._wait_for_services_healthy()
        
        print("Neon Local is ready - Envoy, PgBouncer, and WebSocket proxy are all running")
        
        # Start connection pool monitoring for graceful load handling
        self.start_connection_monitoring()

    def stop_process(self):
        # Stop connection monitoring first
        self.stop_connection_monitoring()
        
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
        
        # Then stop WebSocket proxy
        if self.wsproxy_process:
            print("Stopping WebSocket proxy...")
            self.wsproxy_process.terminate()
            try:
                self.wsproxy_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.wsproxy_process.kill()
                self.wsproxy_process.wait()
            self.wsproxy_process = None
        
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
        
        # Determine application name based on CLIENT environment variable
        client = os.getenv("CLIENT", "").lower()
        app_name = "neon_local_vscode_container" if client == "vscode" else "neon_local_container"
        
        # Use the first database for template substitution
        if databases:
            first_db = databases[0]
            host = first_db['host']
            
            # Perform template variable substitution
            config = template.replace("{role}", first_db['user'])
            config = config.replace("{password}", first_db['password'])
            config = config.replace("{host}", host)
            config = config.replace("{database}", first_db['database'])
            config = config.replace("application_name=neon_local_container", f"application_name={app_name}")
            
            # Generate specific database entries for each database (both transaction and session modes)
            database_entries = []
            for db in databases:
                # Transaction mode entry (explicit)
                transaction_entry = f"{db['database']}=user={db['user']} password={db['password']} host={db['host']} port=5432 dbname={db['database']} application_name={app_name}"
                database_entries.append(transaction_entry)
                
                # Session mode entry (explicit with _session suffix)
                session_entry = f"{db['database']}_session=user={db['user']} password={db['password']} host={db['host']} port=5432 dbname={db['database']} pool_mode=session application_name={app_name}"
                database_entries.append(session_entry)
            
            # Insert specific database entries at the beginning of the [databases] section
            if database_entries:
                databases_section_start = config.find("[databases]")
                if databases_section_start != -1:
                    insert_pos = config.find("\n", databases_section_start) + 1
                    additional_entries = "\n".join(database_entries) + "\n"
                    config = config[:insert_pos] + additional_entries + config[insert_pos:]
            
            # Modify pgbouncer section to listen on port 6432 (internal port)
            config = config.replace("listen_port = 5432", "listen_port = 6432")
        else:
            # Fallback if no databases provided
            config = template.replace("listen_port = 5432", "listen_port = 6432")
        
        with open("/etc/pgbouncer/pgbouncer.ini", "w") as file:
            file.write(config)

    def _write_envoy_config(self, databases):
        template_path = "/scripts/app/envoy/envoy.yaml.tmpl"
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"Envoy config template not found at: {template_path}")

        with open(template_path, "r") as file:
            envoy_template = file.read()

        print(f"Databases: {databases}")
        
        # Build version-aware application name and user agent
        client = os.getenv("CLIENT", "").lower()
        container_version = os.getenv("NEON_LOCAL_CONTAINER_VERSION", "unknown")
        vscode_extension_version = os.getenv("NEON_LOCAL_VSCODE_EXTENSION_VERSION", "unknown")
        
        if client == "vscode" and vscode_extension_version != "unknown":
            # Both container and extension versions
            app_name = f"neon_local_vscode_container_{vscode_extension_version}_{container_version}"
            user_agent_suffix = f"_neon-local-vscode-extension_{vscode_extension_version}_{container_version}"
        elif client == "vscode":
            # VSCode detected but no extension version provided
            app_name = f"neon_local_vscode_container_unknown_{container_version}"
            user_agent_suffix = f"_neon-local-vscode-extension_unknown_{container_version}"
        else:
            # Standalone container only
            app_name = f"neon_local_container_{container_version}"
            user_agent_suffix = f"_neon_local_container_{container_version}"
        
        # Define injection markers
        routes_marker = "              # Database-specific routes will be injected here"
        clusters_marker = "  # Database-specific clusters will be injected here"
        
        # Build database-specific routes
        database_routes = ""
        database_clusters = ""
        
        for db in databases:
            cluster_name = f"neon_cluster_{db['database']}"
            
            # Create routes for this database - WebSocket routes MUST come first!
            database_routes += f"""
              # WebSocket routes for {db['database']} - route to custom WebSocket proxy (MUST be first!)
              - match:
                  prefix: "/{db['database']}"
                  headers:
                  - name: "upgrade"
                    string_match:
                      exact: "websocket"
                route:
                  cluster: wsproxy_cluster
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
                  cluster: wsproxy_cluster
                  timeout: 0s  # No timeout for WebSocket connections
                  upgrade_configs:
                  - upgrade_type: "websocket"
                request_headers_to_add:
                - header:
                    key: "neon-connection-string"
                    value: "postgresql://{db['user']}:{db['password']}@{db['host']}/{db['database']}?sslmode=require&application_name={app_name}"
              
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
"""
            
            # Create cluster for this database
            database_clusters += f"""
  - name: {cluster_name}
    connect_timeout: 30s         # Dramatically increased for cold start and TLS handshake delays
    type: STRICT_DNS
    lb_policy: ROUND_ROBIN
    dns_lookup_family: V4_ONLY
    # DNS resolution optimization for better reliability
    dns_resolution_config:
      resolvers:
      - socket_address:
          address: "8.8.8.8"  # Use Google DNS for faster resolution
          port_value: 53
      - socket_address:
          address: "1.1.1.1"  # Cloudflare DNS as backup
          port_value: 53
      dns_resolver_options:
        use_tcp_for_dns_lookups: false
        no_default_search_domain: true
    # Ultra-optimized circuit breaker settings for concurrent HTTP bursts
    circuit_breakers:
      thresholds:
      - priority: DEFAULT
        max_connections: 10000    # Further increased for concurrent HTTP tests (20x increase)
        max_pending_requests: 10000 # Handle massive concurrent request queues (20x increase)
        max_requests: 50000      # Even more capacity for HTTP endpoint bursts (25x increase)
        max_retries: 100         # Very aggressive proxy-level retry policy (10x increase)
        # Add retry budget to prevent retry storms
        retry_budget:
          budget_percent:
            value: 25.0   # Allow up to 25% of requests to be retries
          min_retry_concurrency: 10
      # Add HIGH priority threshold for critical requests
      - priority: HIGH
        max_connections: 5000    # Reserved capacity for high-priority requests
        max_pending_requests: 5000
        max_requests: 25000
        max_retries: 60
        retry_budget:
          budget_percent:
            value: 20.0   # Slightly lower retry budget for high priority
          min_retry_concurrency: 5
    # Use HTTP/1.1 to avoid HTTP/2 complexity issues
    # http2_protocol_options removed - let Envoy auto-negotiate
    # Enhanced connection pooling and management
    upstream_connection_options:
      tcp_keepalive:
        keepalive_probes: 9        # Increased from 3 for better connection health
        keepalive_time: 300        # Reduced to 5 minutes for faster detection
        keepalive_interval: 30     # Reduced to 30s for more aggressive health checks
    # Add socket options for better connection handling (at cluster level)
    upstream_bind_config:
      socket_options:
      - level: 1      # SOL_SOCKET
        name: 2       # SO_REUSEADDR
        int_value: 1
      - level: 6      # IPPROTO_TCP
        name: 1       # TCP_NODELAY
        int_value: 1
      - level: 1      # SOL_SOCKET  
        name: 15      # SO_REUSEPORT
        int_value: 1
    # Add connection pool settings for better resource management
    typed_extension_protocol_options:
      envoy.extensions.upstreams.http.v3.HttpProtocolOptions:
        "@type": type.googleapis.com/envoy.extensions.upstreams.http.v3.HttpProtocolOptions
        common_http_protocol_options:
          idle_timeout: 300s      # 5 minutes idle timeout
          max_connection_duration: 3600s  # 1 hour max connection duration
          max_headers_count: 100
          max_stream_duration: 300s
        # Add explicit HTTP/1.1 settings for better compatibility
        explicit_http_config:
          http_protocol_options:
            accept_http_10: true
            default_host_for_http_10: "localhost"
    # Simplified HTTP protocol options to avoid configuration errors
    # Focus on essential optimizations only
    # Add outlier detection to remove unhealthy backends automatically
    outlier_detection:
      consecutive_5xx: 20         # More lenient - eject after 20 consecutive 5xx errors
      consecutive_gateway_failure: 15  # More lenient for gateway failures
      interval: 10s               # Check more frequently - every 10 seconds
      base_ejection_time: 10s     # Shorter minimum ejection time for faster recovery
      max_ejection_percent: 30    # Don't eject more than 30% of backends
      split_external_local_origin_errors: true
      success_rate_minimum_hosts: 1
      success_rate_request_volume: 5  # Lower threshold for quicker detection
    # Add health checking for proactive connection management
    health_checks:
    - timeout: 5s
      interval: 10s
      interval_jitter: 2s
      unhealthy_threshold: 3
      healthy_threshold: 2
      # Use HTTP health check instead of TCP for better detection
      http_health_check:
        path: "/sql"
        method: "POST"
        request_headers_to_add:
        - header:
            key: "content-type"
            value: "application/json"
        expected_statuses:
        - start: 200
          end: 299
        - start: 400
          end: 499  # 4xx responses are also considered healthy (application-level errors)
      # Allow health check failures during cold starts
      no_traffic_interval: 30s
      no_traffic_healthy_interval: 60s
      unhealthy_interval: 30s
      unhealthy_edge_interval: 15s
    transport_socket:
      name: envoy.transport_sockets.tls
      typed_config:
        "@type": type.googleapis.com/envoy.extensions.transport_sockets.tls.v3.UpstreamTlsContext
        common_tls_context:
          validation_context:
            # Use system CA certificates for validation
            trusted_ca:
              filename: "/etc/ssl/certs/ca-certificates.crt"
          # TLS optimization for better performance and reliability
          tls_params:
            tls_minimum_protocol_version: TLSv1_2
            tls_maximum_protocol_version: TLSv1_3
            cipher_suites:
            - "ECDHE-ECDSA-AES128-GCM-SHA256"
            - "ECDHE-RSA-AES128-GCM-SHA256"
            - "ECDHE-ECDSA-AES256-GCM-SHA384"
            - "ECDHE-RSA-AES256-GCM-SHA384"
            ecdh_curves:
            - "X25519"
            - "P-256"
        # SNI is critical for Neon
        sni: "{db['host']}"
        # Allow certificate chain validation to be more lenient for cold starts
        allow_renegotiation: true
    load_assignment:
      cluster_name: {cluster_name}
      endpoints:
      - lb_endpoints:
        - endpoint:
            address:
              socket_address:
                address: {db['host']}
                port_value: 443
    # Disable HTTP health checks - Neon /sql endpoint requires POST with JSON body
    # TCP health checks are sufficient for HTTPS connectivity verification
    # Optimized for cold start scenarios - more tolerant of temporary unavailability
    health_checks:
    - timeout: 10s           # Increased from 5s to handle cold start delays
      interval: 30s          # Increased from 10s to reduce aggressive checking
      interval_jitter: 5s    # Increased jitter for better distribution
      unhealthy_threshold: 5  # Increased from 3 to be more tolerant
      healthy_threshold: 1    # Decreased from 2 for faster recovery
      tcp_health_check: {{}}

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

    def _check_wsproxy_health(self):
        """Check if WebSocket proxy is healthy and accepting connections."""
        # WebSocket proxy runs on port 8080
        return self._is_port_open('127.0.0.1', 8080)

    def _wait_for_services_healthy(self, max_wait_time=30, check_interval=0.5):
        """Wait for PgBouncer, WebSocket proxy, and Envoy to be healthy before proceeding."""
        print("Waiting for services to be healthy...")
        
        start_time = time.time()
        pgbouncer_ready = False
        wsproxy_ready = False
        envoy_ready = False
        
        while time.time() - start_time < max_wait_time:
            if not pgbouncer_ready:
                pgbouncer_ready = self._check_pgbouncer_health()
                if pgbouncer_ready:
                    print("✓ PgBouncer is healthy")
            
            if not wsproxy_ready:
                wsproxy_ready = self._check_wsproxy_health()
                if wsproxy_ready:
                    print("✓ WebSocket proxy is healthy")
            
            if not envoy_ready:
                envoy_ready = self._check_envoy_health()
                if envoy_ready:
                    print("✓ Envoy is healthy")
            
            if pgbouncer_ready and wsproxy_ready and envoy_ready:
                print("✓ All services are healthy and ready for traffic")
                return True
            
            time.sleep(check_interval)
        
        # If we get here, services didn't become healthy in time
        pgbouncer_status = "✓" if pgbouncer_ready else "✗"
        wsproxy_status = "✓" if wsproxy_ready else "✗"
        envoy_status = "✓" if envoy_ready else "✗"
        
        print(f"⚠️  Health check timeout after {max_wait_time}s:")
        print(f"   PgBouncer (port 6432): {pgbouncer_status}")
        print(f"   WebSocket proxy (port 8080): {wsproxy_status}")
        print(f"   Envoy (port 5432): {envoy_status}")
        print("Services may not be fully ready for traffic")
        
        return False

    def start_connection_monitoring(self):
        """Start connection pool monitoring to prevent exhaustion."""
        if self.connection_monitor_thread is None:
            self.connection_monitor_thread = threading.Thread(
                target=self._monitor_connection_pools, 
                daemon=True
            )
            self.connection_monitor_thread.start()
            logging.info("Connection pool monitoring started")

    def _monitor_connection_pools(self):
        """Monitor PgBouncer health and trigger recovery when needed (without waking backend database)."""
        while self.monitoring_enabled:
            try:
                # Check PgBouncer health and stats
                pgbouncer_healthy = self._check_pgbouncer_stats()
                
                # Check Envoy stats via admin interface  
                self._check_envoy_stats()
                
                # If PgBouncer is unhealthy, trigger recovery
                if not pgbouncer_healthy:
                    logging.warning("PgBouncer appears unhealthy - triggering recovery")
                    self._trigger_pgbouncer_recovery()
                
                # Sleep for 60 seconds between checks (less frequent to avoid keeping backend awake)
                time.sleep(60)
                
            except Exception as e:
                logging.error(f"Connection monitoring error: {e}")
                time.sleep(60)  # Wait longer on error

    def _check_pgbouncer_stats(self):
        """Check PgBouncer health without waking up the backend database."""
        try:
            # Primary health check - is the process still running?
            if self.pgbouncer_process and self.pgbouncer_process.poll() is not None:
                logging.error(f"PgBouncer process has exited with code {self.pgbouncer_process.returncode}")
                return False
            
            # Secondary check - can we connect to PgBouncer port?
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(('127.0.0.1', 6432))
            sock.close()
            
            if result != 0:
                logging.warning(f"PgBouncer port check failed (error {result}) - may be overloaded or crashed")
                return False
            
            # Third check - analyze PgBouncer logs for recent errors (doesn't wake backend)
            return self._analyze_pgbouncer_logs()
                
        except Exception as e:
            logging.error(f"PgBouncer health check error: {e}")
            return False

    def _analyze_pgbouncer_logs(self):
        """Analyze recent PgBouncer log entries to detect health issues without database connections."""
        try:
            import re
            from datetime import datetime, timezone
            
            log_file = "/var/log/pgbouncer.log"
            
            # Check if log file exists
            if not os.path.exists(log_file):
                return True
            
            # Read last 100 lines of the log file for analysis
            lines_to_check = 100
            recent_lines = []
            
            with open(log_file, 'r') as f:
                lines = f.readlines()
                recent_lines = lines[-lines_to_check:] if len(lines) > lines_to_check else lines
            
            # Define error patterns that indicate REAL PgBouncer health issues
            # Exclude normal database suspension behavior
            critical_patterns = [
                'FATAL',
                'PANIC', 
                'too many clients',
                'out of memory',
                'pooler error',
                'max_client_conn reached',
                'pool_size reached',
                'server login failed'  # Real auth failures, not suspension
            ]
            
            # Patterns that are NORMAL during database suspension - ignore these
            suspension_normal_patterns = [
                'server conn crashed?',  # Normal when database suspends
                'got packet \'E\' from server when not linked',  # Normal suspension signal
                'closing because: server conn crashed?',  # Normal cleanup during suspension
                'client unexpected eof',  # Normal when client disconnects
                'client close request',  # Normal client disconnection
                'query_timeout',  # Normal when database auto-suspends during long queries
                'client_login_timeout',  # Normal when database is slow to wake up from suspension
                'pooler error: query_timeout',  # Normal timeout during suspension
                'pooler error: client_login_timeout',  # Normal login timeout during suspension
                'closing because: query_timeout',  # Normal cleanup after query timeout
                'closing because: client_login_timeout'  # Normal cleanup after login timeout
            ]
            
            # Get current time for timestamp analysis
            current_time = time.time()
            
            # Only analyze logs since our last check (avoid re-processing old errors)
            check_time_threshold = max(self.last_log_check_time, self.pgbouncer_start_time)
            
            # Update last check time for next iteration
            self.last_log_check_time = current_time
            
            # Count NEW errors since last check
            new_critical_errors = 0
            log_entries_analyzed = 0
            
            for line in recent_lines:
                line_lower = line.lower().strip()
                if not line_lower:
                    continue
                
                # Parse PgBouncer timestamp: "YYYY-MM-DD HH:MM:SS.mmm UTC"
                timestamp_match = re.match(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}) UTC', line)
                if not timestamp_match:
                    continue
                
                try:
                    # Convert timestamp to epoch time
                    timestamp_str = timestamp_match.group(1)
                    log_time = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S.%f')
                    log_time = log_time.replace(tzinfo=timezone.utc)
                    log_epoch = log_time.timestamp()
                    
                    # Only analyze logs since our last check
                    if log_epoch <= check_time_threshold:
                        continue
                        
                    log_entries_analyzed += 1
                    
                    # Skip entries that are normal during database suspension
                    if any(pattern in line_lower for pattern in suspension_normal_patterns):
                        continue
                    
                    # Check for critical errors (real issues, not suspension-related)
                    if any(pattern in line_lower for pattern in critical_patterns):
                        new_critical_errors += 1
                        # Only log at DEBUG level to avoid spam
                        logging.debug(f"PgBouncer critical error detected: {line.strip()}")
                        
                except Exception as e:
                    # Skip lines that can't be parsed
                    continue
            
            # Health assessment based on NEW errors only
            if new_critical_errors > 0:
                logging.error(f"PgBouncer health check: {new_critical_errors} NEW critical errors found since last check")
                return False
            
            # Log summary at debug level (analyzed X entries, found Y issues)
            if log_entries_analyzed > 0:
                logging.debug(f"PgBouncer log analysis: analyzed {log_entries_analyzed} new log entries, no critical issues found")
            
            return True
            
        except Exception as e:
            logging.debug(f"PgBouncer log analysis error: {e}")
            # If we can't read logs, assume healthy (fail open)
            return True

    def _check_envoy_stats(self):
        """Check Envoy connection statistics via admin interface."""
        try:
            # Query Envoy admin interface for circuit breaker stats
            response = requests.get('http://127.0.0.1:9901/stats?filter=circuit_breakers', timeout=2)
            if response.status_code == 200:
                stats_text = response.text
                
                # Check for circuit breaker openings
                if 'cx_open' in stats_text and any(line.endswith('1') for line in stats_text.split('\n') if 'cx_open' in line):
                    logging.warning("Envoy circuit breakers are opening - high load detected")
                
                # Check connection counts
                for line in stats_text.split('\n'):
                    if 'remaining' in line and int(line.split(': ')[-1]) < 100:
                        logging.warning(f"Envoy connection pool approaching limit: {line}")
                        
        except Exception as e:
            logging.debug(f"Envoy stats check error: {e}")

    def stop_connection_monitoring(self):
        """Stop connection pool monitoring."""
        self.monitoring_enabled = False
        self.recovery_enabled = False
        if self.connection_monitor_thread:
            self.connection_monitor_thread.join(timeout=5)
            logging.info("Connection pool monitoring stopped")

    def _trigger_pgbouncer_recovery(self):
        """Trigger PgBouncer recovery in a separate thread to avoid blocking monitoring."""
        if not self.recovery_enabled:
            return
            
        # Check if we're in cooldown period
        current_time = time.time()
        if current_time - self.last_pgbouncer_restart < self.restart_cooldown:
            logging.info(f"PgBouncer restart in cooldown (last restart {current_time - self.last_pgbouncer_restart:.0f}s ago)")
            return
            
        # Check if we've exceeded maximum restart attempts
        if self.pgbouncer_restart_count >= self.max_pgbouncer_restarts:
            logging.error(f"PgBouncer restart limit exceeded ({self.max_pgbouncer_restarts} restarts)")
            return
        
        # Start recovery in a separate thread
        if self.recovery_thread is None or not self.recovery_thread.is_alive():
            self.recovery_thread = threading.Thread(
                target=self._perform_pgbouncer_recovery,
                daemon=True
            )
            self.recovery_thread.start()

    def _perform_pgbouncer_recovery(self):
        """Perform graceful PgBouncer recovery."""
        try:
            logging.info("🔄 Starting PgBouncer graceful recovery...")
            
            # Step 1: Try graceful connection cleanup first
            if self._attempt_pgbouncer_cleanup():
                logging.info("✅ PgBouncer recovered via connection cleanup")
                return
            
            # Step 2: Try graceful restart
            if self._attempt_pgbouncer_restart():
                logging.info("✅ PgBouncer recovered via graceful restart")
                return
            
            # Step 3: Force restart as last resort
            if self._attempt_pgbouncer_force_restart():
                logging.info("✅ PgBouncer recovered via force restart")
                return
                
            logging.error("❌ PgBouncer recovery failed - all recovery methods exhausted")
            
        except Exception as e:
            logging.error(f"PgBouncer recovery exception: {e}")

    def _attempt_pgbouncer_cleanup(self):
        """Attempt to clean up PgBouncer connections without restarting."""
        try:
            logging.info("🧹 Attempting PgBouncer connection cleanup...")
            
            # Check if PgBouncer process is still running
            if not self.pgbouncer_process or self.pgbouncer_process.poll() is not None:
                logging.warning("PgBouncer process is not running - skipping cleanup, will restart")
                return False
            
            # For real connection issues, we should restart rather than suspend
            # Suspending PgBouncer breaks the entire proxy layer
            logging.info("PgBouncer is running but unhealthy - proceeding to restart for reliability")
            return False  # Skip cleanup, go straight to restart
            
        except Exception as e:
            logging.warning(f"PgBouncer cleanup check failed: {e}")
            return False

    def _attempt_pgbouncer_restart(self):
        """Attempt graceful PgBouncer restart."""
        try:
            logging.info("🔄 Attempting graceful PgBouncer restart...")
            
            # Update restart tracking
            self.pgbouncer_restart_count += 1
            self.last_pgbouncer_restart = time.time()
            
            # Stop current PgBouncer process gracefully
            if self.pgbouncer_process:
                logging.info("Stopping current PgBouncer process...")
                self.pgbouncer_process.terminate()
                try:
                    self.pgbouncer_process.wait(timeout=10)  # Give it time to shutdown gracefully
                    logging.info("PgBouncer stopped gracefully")
                except subprocess.TimeoutExpired:
                    logging.warning("PgBouncer graceful shutdown timed out, killing...")
                    self.pgbouncer_process.kill()
                    self.pgbouncer_process.wait()
                self.pgbouncer_process = None
            
            # Wait a moment for port to be released
            time.sleep(2)
            
            # Restart PgBouncer with same configuration
            logging.info("Starting new PgBouncer process...")
            pgbouncer_env = os.environ.copy()
            if hasattr(self, 'database_params') and self.database_params:
                endpoint_id = self.database_params[0]['host'].split('.')[0]
                pgbouncer_env['PGOPTIONS'] = f'-c endpoint={endpoint_id}'
                pgbouncer_env['RES_OPTIONS'] = 'inet inet6:off'
                pgbouncer_env['RESOLV_HOST_CONF'] = '/dev/null'
            
            with open("/var/log/pgbouncer.log", "a") as log:
                self.pgbouncer_process = subprocess.Popen([
                    "/usr/local/bin/pgbouncer_wrapper.sh", "/etc/pgbouncer/pgbouncer.ini"
                ], stdout=log, stderr=log, env=pgbouncer_env)
            
            # Track when PgBouncer was restarted for log analysis
            self.pgbouncer_start_time = time.time()
            
            # Wait for PgBouncer to be ready
            max_wait = 15
            for i in range(max_wait):
                time.sleep(1)
                if self._check_pgbouncer_health():
                    logging.info(f"PgBouncer restarted successfully (took {i+1}s)")
                    return True
            
            logging.error("PgBouncer restart failed - not responding after 15s")
            return False
            
        except Exception as e:
            logging.error(f"PgBouncer graceful restart failed: {e}")
            return False

    def _attempt_pgbouncer_force_restart(self):
        """Force restart PgBouncer as last resort."""
        try:
            logging.warning("⚠️  Attempting PgBouncer force restart (last resort)...")
            
            # Kill current process if it exists
            if self.pgbouncer_process:
                logging.info("Force killing PgBouncer process...")
                self.pgbouncer_process.kill()
                self.pgbouncer_process.wait()
                self.pgbouncer_process = None
            
            # Wait for port to be released
            time.sleep(3)
            
            # Force restart with same logic as graceful restart
            return self._attempt_pgbouncer_restart()
            
        except Exception as e:
            logging.error(f"PgBouncer force restart failed: {e}")
            return False