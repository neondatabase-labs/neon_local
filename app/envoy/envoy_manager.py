import os
import json
import subprocess
import yaml
from app.process_manager import ProcessManager
from app.neon import NeonAPI

class EnvoyManager(ProcessManager):
    def __init__(self):
        super().__init__()
        self.envoy_process = None

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
            
        self._write_envoy_config(params)

    def start_process(self):
        self.prepare_config()
        with open("/var/log/envoy.log", "a") as log:
            self.envoy_process = subprocess.Popen([
                "envoy", "-c", "/tmp/envoy.yaml", "--log-level", "info"
            ], stdout=log, stderr=log)
        print("Neon Local is ready")

    def stop_process(self):
        if self.envoy_process:
            print("Stopping Envoy...")
            self.envoy_process.terminate()
            try:
                self.envoy_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.envoy_process.kill()
                self.envoy_process.wait()
            self.envoy_process = None

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
        
        # Build database-specific configuration
        database_routes = []
        database_clusters = []
        
        for db in databases:
            cluster_name = f"neon_cluster_{db['database']}"
            
            # Create route for this database
            database_route = {
                "match": {
                    "prefix": "/",
                    "headers": [
                        {
                            "name": "neon-connection-string",
                            "string_match": {
                                "contains": db['database']
                            }
                        }
                    ]
                },
                "route": {
                    "cluster": cluster_name,
                    "timeout": "30s"
                }
            }
            
            # Also route /{database} paths
            database_path_route = {
                "match": {
                    "prefix": f"/{db['database']}"
                },
                "route": {
                    "cluster": cluster_name,
                    "timeout": "30s"
                }
            }
            
            database_routes.extend([database_route, database_path_route])
            
            # Create cluster for this database
            cluster_config = f"""
  - name: {cluster_name}
    connect_timeout: 5s
    type: STATIC
    lb_policy: ROUND_ROBIN
    transport_socket:
      name: envoy.transport_sockets.tls
      typed_config:
        "@type": type.googleapis.com/envoy.extensions.transport_sockets.tls.v3.UpstreamTlsContext
        sni: {db['host']}
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
            key: "host"
            value: "{db['host']}"
        - header:
            key: "user-agent"
            value: "envoy-health-check{user_agent_suffix}"
        - header:
            key: "content-type"
            value: "application/json"
    typed_extension_protocol_options:
      envoy.extensions.upstreams.http.v3.HttpProtocolOptions:
        "@type": type.googleapis.com/envoy.extensions.upstreams.http.v3.HttpProtocolOptions
        explicit_http_config:
          http2_protocol_options: {{}}"""

            database_clusters.append(cluster_config)
        
        # Generate routes YAML
        routes_yaml = ""
        for i, route in enumerate(database_routes):
            routes_yaml += f"""
              - match:
                  prefix: "/"
                  headers:
                  - name: "neon-connection-string"
                    string_match:
                      contains: "{databases[i//2]['database']}"
                route:
                  cluster: neon_cluster_{databases[i//2]['database']}
                  timeout: 30s
                  request_headers_to_add:
                  - header:
                      key: "neon-connection-string"
                      value: "postgresql://{databases[i//2]['user']}:{databases[i//2]['password']}@{databases[i//2]['host']}/{databases[i//2]['database']}?sslmode=require&application_name={app_name}"
                  - header:
                      key: "host"
                      value: "{databases[i//2]['host']}"
                  - header:
                      key: "user-agent"
                      value: "%REQ(user-agent)%{user_agent_suffix}"
                  - header:
                      key: "connection"
                      value: "keep-alive"
                  - header:
                      key: "content-type"
                      value: "application/json"
              - match:
                  prefix: "/{databases[i//2]['database']}"
                route:
                  cluster: neon_cluster_{databases[i//2]['database']}
                  timeout: 30s
                  request_headers_to_add:
                  - header:
                      key: "neon-connection-string" 
                      value: "postgresql://{databases[i//2]['user']}:{databases[i//2]['password']}@{databases[i//2]['host']}/{databases[i//2]['database']}?sslmode=require&application_name={app_name}"
                  - header:
                      key: "host"
                      value: "{databases[i//2]['host']}"
                  - header:
                      key: "user-agent"
                      value: "%REQ(user-agent)%{user_agent_suffix}"
                  - header:
                      key: "connection"
                      value: "keep-alive"
                  - header:
                      key: "content-type"
                      value: "application/json"
"""
            if i % 2 == 1:  # Only process every other route to avoid duplicates
                break
        
        # Create database-specific clusters YAML
        clusters_yaml = "\n".join(database_clusters)
        
        # Update default cluster if we have databases
        if databases:
            first_db = databases[0]
            default_cluster_replacement = f"neon_cluster_{first_db['database']}"
            envoy_template = envoy_template.replace("default_neon_cluster", default_cluster_replacement)
        
        # Inject configurations into template
        envoy_config = envoy_template.replace(routes_marker, routes_yaml)
        envoy_config = envoy_config.replace(clusters_marker, clusters_yaml)

        with open("/tmp/envoy.yaml", "w") as file:
            file.write(envoy_config)
