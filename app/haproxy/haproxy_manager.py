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
            
        self._write_haproxy_config(params)

    def start_process(self):
        self.prepare_config()
        with open("/var/log/haproxy.log", "a") as log:
            self.haproxy_process = subprocess.Popen([
                "haproxy", "-f", "/tmp/haproxy.cfg"
            ], stdout=log, stderr=log)
        print("Neon Local is ready")

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

    def _write_haproxy_config(self, databases):
        template_path = "/scripts/app/haproxy/haproxy.cfg.tmpl"
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"HAProxy config template not found at: {template_path}")

        with open(template_path, "r") as file:
            haproxy_template = file.read()

        print(f"Databases: {databases}")
        print(f"Debug: Using template at {template_path}")
        
        # Determine application name and user agent suffix based on CLIENT environment variable
        client = os.getenv("CLIENT", "").lower()
        app_name = "neon_local_vscode_container" if client == "vscode" else "neon_local_container"
        user_agent_suffix = "_neon_local_vscode_container" if client == "vscode" else "_neon_local_container"
        
        # Define injection markers (handle both old and new template formats)
        acl_marker = "    # Database-specific ACLs will be injected here"
        routing_marker = "    # Database-specific routing rules will be injected here"
        backend_marker = "# Database-specific backends will be injected here"
        
        # Fallback to old markers if new ones don't exist
        if acl_marker not in haproxy_template:
            acl_marker = "    # Route HTTP traffic to database-specific backends (rules will be injected dynamically)"
        if routing_marker not in haproxy_template:
            routing_marker = "    # Frontend routing rules will be added here"
        if backend_marker not in haproxy_template:
            backend_marker = "# Database-specific backends will be added here"
        
        # Build the database-specific frontend ACLs
        frontend_acls = "\n    # Database-specific ACLs\n    acl is_sql path_beg /sql"
        
        # Generate backend sections and frontend routing rules for each database
        backend_sections = []
        frontend_routing_rules = ""
        
        for db in databases:
            backend_name = f"backend_{db['database']}"
            
            # Add frontend ACLs and routing rules for this database
            frontend_acls += f"""
    acl is_{db['database']} path_beg /{db['database']}
    acl is_{db['database']}_connection hdr(Neon-Connection-String) -m reg -i {db['database']}
    acl is_sql_path_for_{db['database']} path_beg /sql"""
            
            frontend_routing_rules += f"""
    use_backend {backend_name} if is_{db['database']}
    use_backend {backend_name} if is_{db['database']}_connection
    use_backend {backend_name} if is_sql_path_for_{db['database']} is_{db['database']}_connection"""
            
            # Create backend section with HTTP/1.1 keep-alive support  
            backend_config = f"""
backend {backend_name}
    mode http
    
    # Optimized timeouts for faster response
    timeout connect 3s
    timeout client 30s
    timeout server 30s
    timeout http-request 8s
    timeout http-keep-alive 5s
    timeout check 3s
    
    # HTTP/1.1 Keep-Alive options
    option http-keep-alive
    option prefer-last-server
    option http-pretend-keepalive
    option http-server-close
    option httplog
    
    # Error handling optimizations
    option redispatch
    retries 2
    
    # Backend server configuration with connection optimizations
    server ws_server1 {db['host']}:443 ssl verify none sni str({db['host']}) check maxconn 100 check inter 2s fastinter 1s downinter 2s rise 1 fall 2 
    
    # HTTP/1.1 Keep-Alive headers and request modification
    http-request set-header Neon-Connection-String "postgresql://{db['user']}:{db['password']}@{db['host']}/{db['database']}?sslmode=require&application_name={app_name}"
    http-request set-header Host {db['host']}
    http-request set-header User-Agent "%[req.hdr(User-Agent)]{user_agent_suffix}"
    http-request set-header Connection "keep-alive"
    
    # Preserve critical Neon serverless driver headers (pass through from client)
    # These headers are automatically passed through since we're not removing them
    # Just ensure Content-Type is properly handled for JSON requests
    http-request set-header Content-Type "application/json" if !{ hdr(Content-Type) -m found }
    
    # Response headers for client keep-alive support
    http-response set-header Connection "keep-alive"
    http-response set-header Keep-Alive "timeout=30, max=100"
    http-response set-header Cache-Control "no-cache, no-store, must-revalidate"
    
    # Ensure proper HTTP/1.1 handling
    http-response set-header Server "HAProxy-Neon-Local"
"""
            backend_sections.append(backend_config)
        
        # Add fallback routing for HTTP requests without specific database headers
        if databases:
            first_db = databases[0]
            default_backend = f"backend_{first_db['database']}"
            frontend_routing_rules += f"""
    # Fallback HTTP routing for requests without specific database headers
    use_backend {default_backend} if is_http_method is_http11
    use_backend {default_backend} if is_http_method has_host_header
    use_backend {default_backend} if is_sql_path
    use_backend {default_backend} if is_post_method"""
        
        # Create the database-specific backends section
        database_backends = "\n".join(backend_sections)
        
        # Debug output
        print(f"Debug: Generated ACLs: {frontend_acls}")
        print(f"Debug: Generated routing rules: {frontend_routing_rules}")
        print(f"Debug: Generated backends count: {len(backend_sections)}")
        
        # Inject configurations into template
        haproxy_config = haproxy_template
        
        # Inject ACLs before routing rules (combine with the ACL marker line)
        acl_injection = acl_marker + frontend_acls
        haproxy_config = haproxy_config.replace(acl_marker, acl_injection)
        
        # Inject routing rules  
        routing_injection = routing_marker + frontend_routing_rules
        haproxy_config = haproxy_config.replace(routing_marker, routing_injection)
        
        # Inject backends
        backend_injection = backend_marker + "\n" + database_backends
        haproxy_config = haproxy_config.replace(backend_marker, backend_injection)

        with open("/tmp/haproxy.cfg", "w") as file:
            file.write(haproxy_config)
