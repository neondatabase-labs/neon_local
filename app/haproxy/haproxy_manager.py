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
        
        # Find where to insert the database-specific configuration
        # Look for the comment "# Backend selection rules will be added here"
        replacement_marker = "# Backend selection rules will be added here"
        
        if replacement_marker not in haproxy_template:
            raise ValueError(f"Template marker '{replacement_marker}' not found in haproxy.cfg.tmpl")
        
        # Split template at the replacement marker
        template_parts = haproxy_template.split(replacement_marker)
        template_before = template_parts[0]
        template_after = template_parts[1] if len(template_parts) > 1 else ""
        
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
    acl is_{db['database']}_connection hdr(Neon-Connection-String) -m reg -i {db['database']}"""
            
            frontend_routing_rules += f"""
    use_backend {backend_name} if is_{db['database']} or is_sql is_{db['database']}_connection"""
            
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
    
    # Response headers for client keep-alive support
    http-response set-header Connection "keep-alive"
    http-response set-header Keep-Alive "timeout=30, max=100"
    http-response set-header Cache-Control "no-cache, no-store, must-revalidate"
    
    # Ensure proper HTTP/1.1 handling
    http-response set-header Server "HAProxy-Neon-Local"
"""
            backend_sections.append(backend_config)
        
        # Add default backend rule using the first database
        if databases:
            first_db = databases[0]
            default_backend = f"backend_{first_db['database']}"
            frontend_routing_rules += f"\n    default_backend {default_backend}"
        
        # Inject the database-specific configuration into the template
        database_config = frontend_acls + frontend_routing_rules
        backend_config_section = "\n\n" + "\n".join(backend_sections)
        
        # Combine template parts with generated configuration
        haproxy_config = template_before + database_config + template_after + backend_config_section

        with open("/tmp/haproxy.cfg", "w") as file:
            file.write(haproxy_config)
