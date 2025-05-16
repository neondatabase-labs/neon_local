import os
import requests
import json

API_URL = "https://console.neon.tech/api/v2"

class NeonAPI:
    def __init__(self):
        self.api_key = os.getenv("NEON_API_KEY")
        self.project_id = os.getenv("NEON_PROJECT_ID")

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def get_endpoint_host(self, project_id, branch_id):
        if not self.api_key:
            raise ValueError("NEON_API_KEY not set.")
        if not project_id:
            raise ValueError("NEON_PROJECT_ID not set.")
        if not branch_id:
            raise ValueError("BRANCH_ID not set.")
        
        try:
            endpoint_url = f"{API_URL}/projects/{project_id}/endpoints"
            endpoint_response = requests.get(endpoint_url, headers=self._headers())
            endpoint_response.raise_for_status()
            endpoint_json = endpoint_response.json()
            
            if not endpoint_json.get("endpoints"):
                raise ValueError("No endpoints found for the branch")
            
            # Find the first read_write endpoint for the branch
            for endpoint in endpoint_json["endpoints"]:
                if endpoint.get("branch_id") == branch_id and endpoint.get("type") == "read_write":
                    if not endpoint.get("host"):
                        raise ValueError("Endpoint host not found in response")
                    return endpoint["host"]
            
            raise ValueError(f"No read_write endpoint found for branch {branch_id}")
            
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Failed to fetch endpoint information: {str(e)}")
    
    def get_database_name_and_owner(self, project_id, branch_id):
        if not self.api_key:
            raise ValueError("NEON_API_KEY not set.")
        if not project_id:
            raise ValueError("NEON_PROJECT_ID not set.")
        if not branch_id:
            raise ValueError("BRANCH_ID not set.")

        try:
            url = f"{API_URL}/projects/{project_id}/branches/{branch_id}/databases"
            response = requests.get(url, headers=self._headers())
            response.raise_for_status()
            json_response = response.json()

            if not json_response.get("databases"):
                raise ValueError("No databases found in the branch response")

            databases = []
            for database in json_response["databases"]:
                if not database.get("name") or not database.get("owner_name"):
                    print(f"Warning: Database {database.get('name', 'unknown')} missing name or owner, skipping")
                    continue

                databases.append({
                    "database": database["name"],
                    "user": database["owner_name"]
                })

            if not databases:
                raise ValueError("No valid databases found in the branch response")

            return databases

        except Exception as e:
            print(f"Debug: Error getting connection info: {str(e)}")
            raise
    
    def get_database_owner_password(self, project_id, branch_id, user):
        if not self.api_key:
            raise ValueError("NEON_API_KEY not set.")
        if not project_id:
            raise ValueError("NEON_PROJECT_ID not set.")
        if not branch_id:
            raise ValueError("BRANCH_ID not set.")
        if not user:
            raise ValueError("User not provided.")
        
        try:
            url = f"{API_URL}/projects/{project_id}/branches/{branch_id}/roles/{user}/reveal_password"
            response = requests.get(url, headers=self._headers())
            response.raise_for_status()
            json_response = response.json()
            
            if not json_response.get("password"):
                raise ValueError("Password not found in the response")
            
            return json_response["password"]
            
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Failed to fetch password: {str(e)}")

    def get_branch_connection_info(self, project_id, branch_id):
        if not self.api_key:
            raise ValueError("NEON_API_KEY not set.")
        if not project_id:
            raise ValueError("NEON_PROJECT_ID not set.")
        if not branch_id:
            raise ValueError("BRANCH_ID not set.")

        databases = self.get_database_name_and_owner(project_id, branch_id)
        host = self.get_endpoint_host(project_id, branch_id)
        
        # Add password to each database entry
        for db_info in databases:
            db_info["password"] = self.get_database_owner_password(project_id, branch_id, db_info["user"])
            db_info["host"] = host
        
        return databases
        
    def cleanup_branch(self, state, current_branch):
        if not self.api_key or not self.project_id:
            print("No NEON_API_KEY or NEON_PROJECT_ID set, skipping Neon cleanup.")
            return state
        if current_branch is None:
            current_branch = "None"
        params = state.get(current_branch)
        if params:
            try:
                # Handle both old and new state formats
                branch_id = params.get("branch_id")
                if not branch_id:
                    print("No branch_id found in state, skipping cleanup")
                    return state
                    
                requests.get(f"{API_URL}/projects/{self.project_id}/branches/{branch_id}",
                             headers=self._headers()).raise_for_status()
            except:
                print("Branch not found at Neon.")
                params = None

            if params:
                response = requests.delete(
                    f"{API_URL}/projects/{self.project_id}/branches/{branch_id}",
                    headers=self._headers())
                print(response)
                response.raise_for_status()
                print(response.json())

        if current_branch in state:
            print(f"Removing branch state: {state.pop(current_branch)}")

        return state

    def _get_available_branch_name(self, base_name):
        """Get an available branch name by appending a number if needed."""
        try:
            # Get all existing branches
            branches_response = requests.get(f"{API_URL}/projects/{self.project_id}/branches",
                                           headers=self._headers())
            branches_response.raise_for_status()
            branches = branches_response.json().get("branches", [])
            
            # Get all existing branch names
            existing_names = {branch.get("name") for branch in branches if branch.get("name")}
            
            # If base name is available, use it
            if base_name not in existing_names:
                return base_name
            
            # Try appending numbers until we find an available name
            counter = 2
            while True:
                new_name = f"{base_name}_{counter}"
                if new_name not in existing_names:
                    return new_name
                counter += 1
                
        except requests.exceptions.RequestException as e:
            print(f"Error checking branch names: {str(e)}")
            raise

    def fetch_or_create_branch(self, state, current_branch, parent_branch_id=None, vscode=False):
        if not self.api_key or not self.project_id:
            raise ValueError("NEON_API_KEY or NEON_PROJECT_ID not set.")

        branch_id = None
        if current_branch and current_branch in state:
            try:
                branch_id = state[current_branch]["branch_id"]
                # Verify branch still exists
                requests.get(f"{API_URL}/projects/{self.project_id}/branches/{branch_id}",
                             headers=self._headers()).raise_for_status()
            except:
                print("No branch found at Neon.")
                branch_id = None

        if branch_id is None:
            try:
                # Get an available branch name
                branch_name = self._get_available_branch_name(current_branch) if current_branch else None
                if branch_name != current_branch:
                    print(f"Branch name '{current_branch}' already exists, using '{branch_name}' instead")
                
                # Create new branch
                payload = {
                    "annotation_value": {"neon_local": "true"},
                    "endpoints": [{"type": "read_write"}]
                }

                if parent_branch_id or branch_name:
                    payload["branch"] = {}
                    if parent_branch_id:
                        payload["branch"]["parent_id"] = parent_branch_id
                    if branch_name:
                        payload["branch"]["name"] = branch_name
                if vscode:
                    payload["annotation_value"]["vscode"] = "true"

                response = requests.post(f"{API_URL}/projects/{self.project_id}/branches",
                                         headers=self._headers(), json=payload)
                response.raise_for_status()
                json_response = response.json()
                branch_id = json_response["branch"]["id"]
                
            except requests.exceptions.RequestException as e:
                print(f"Error creating branch: {str(e)}")
                raise

        if not branch_id:
            raise ValueError("Failed to get branch ID")

        # Get connection info for the branch
        connection_info = self.get_branch_connection_info(self.project_id, branch_id)
        
        # Add branch_id to each connection info object
        for info in connection_info:
            info["branch_id"] = branch_id
        
        # Store branch ID in state using the original branch name
        if current_branch:
            state[current_branch] = {"branch_id": branch_id}
        else:
            state['None'] = {"branch_id": branch_id}

        return connection_info, state
