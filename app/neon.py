import os
import requests

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
