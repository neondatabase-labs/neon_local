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
        
        # First get the branch details to get the endpoint_id
        endpoint_url = f"{API_URL}/projects/{project_id}/endpoints"
        endpoint_response = requests.get(endpoint_url, headers=self._headers())
        endpoint_response.raise_for_status()
        endpoint_json = endpoint_response.json()
        
        if len(endpoint_json["endpoints"]) == 0:
            raise ValueError("No endpoints found for the branch")
        else:
            for endpoint in endpoint_json["endpoints"]:
                if endpoint["branch_id"] == branch_id and endpoint["type"] == "read_write":
                    return endpoint["host"]
            else:
                raise ValueError("Endpoint not found for the branch")
    
    def get_database_name_and_owner(self, project_id, branch_id):
        if not self.api_key:
            raise ValueError("NEON_API_KEY not set.")
        if not project_id:
            raise ValueError("NEON_PROJECT_ID not set.")
        if not branch_id:
            raise ValueError("BRANCH_ID not set.")
        
        url = f"{API_URL}/projects/{project_id}/branches/{branch_id}/databases"
        response = requests.get(url, headers=self._headers())
        response.raise_for_status()
        json_response = response.json()
        if len(json_response["databases"]) == 0:
            raise ValueError("No databases found in the branch response")
        return {"database": json_response["databases"][0]["name"], "user": json_response["databases"][0]["owner_name"]}
    
    def get_database_owner_password(self, project_id, branch_id, user):
        if not self.api_key:
            raise ValueError("NEON_API_KEY not set.")
        if not project_id:
            raise ValueError("NEON_PROJECT_ID not set.")
        if not branch_id:
            raise ValueError("BRANCH_ID not set.")
        if not user:
            raise ValueError("User not provided.")
        
        url = f"{API_URL}/projects/{project_id}/branches/{branch_id}/roles/{user}/reveal_password"
        response = requests.get(url, headers=self._headers())
        response.raise_for_status()
        json_response = response.json()
        if "password" not in json_response:
            raise ValueError("Password not found in the response")
        return json_response["password"]

    def get_branch_connection_info(self, project_id, branch_id):
        if not self.api_key:
            raise ValueError("NEON_API_KEY not set.")
        if not project_id:
            raise ValueError("NEON_PROJECT_ID not set.")
        if not branch_id:
            raise ValueError("BRANCH_ID not set.")

        database_info = self.get_database_name_and_owner(project_id, branch_id)
        password = self.get_database_owner_password(project_id, branch_id, database_info["user"])
        return {
            "host": self.get_endpoint_host(project_id, branch_id),
            "database": database_info["database"],
            "password": password,
            "role": database_info["user"]
        }
        
    def cleanup_branch(self, state, current_branch):
        if not self.api_key or not self.project_id:
            print("No NEON_API_KEY or NEON_PROJECT_ID set, skipping Neon cleanup.")
            return state
        if current_branch is None:
            current_branch = "None"
        params = state.get(current_branch)
        if params:
            try:
                requests.get(f"{API_URL}/projects/{self.project_id}/branches/{params['branch_id']}",
                             headers=self._headers()).raise_for_status()
            except:
                print("Branch not found at Neon.")
                params = None

            if params:
                response = requests.delete(
                    f"{API_URL}/projects/{self.project_id}/branches/{params['branch_id']}",
                    headers=self._headers())
                print(response)
                response.raise_for_status()
                print(response.json())

        if current_branch in state:
            print(f"Removing branch state: {state.pop(current_branch)}")

        return state

    def fetch_or_create_branch(self, state, current_branch, parent_branch_id=None):
        if not self.api_key or not self.project_id:
            raise ValueError("NEON_API_KEY or NEON_PROJECT_ID not set.")

        params = state.get(current_branch) if current_branch else None
        if params:
            try:
                requests.get(f"{API_URL}/projects/{self.project_id}/branches/{params['branch_id']}",
                             headers=self._headers()).raise_for_status()
            except:
                print("No branch found at Neon.")
                params = None

        if params is None:
            if parent_branch_id:
                payload = {"endpoints": [{"type": "read_write"}], "branch": {"parent_id": parent_branch_id}}
            else:
                payload = {"endpoints": [{"type": "read_write"}]}
            response = requests.post(f"{API_URL}/projects/{self.project_id}/branches",
                                     headers=self._headers(), json=payload)
            response.raise_for_status()
            json_response = response.json()
            params = json_response["connection_uris"][0]["connection_parameters"]
            params["branch_id"] = json_response["branch"]["id"]
            if current_branch:
                state[current_branch] = params
            else:
                state['None'] = params

        return params, state
