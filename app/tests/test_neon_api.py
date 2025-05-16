import unittest
from unittest.mock import patch, MagicMock
import os
import json
from app.neon import NeonAPI

class TestNeonAPI(unittest.TestCase):
    def setUp(self):
        self.api = NeonAPI()
        self.api.api_key = "test_api_key"
        self.api.project_id = "test_project_id"
        self.test_branch_id = "test_branch_id"

    @patch.dict(os.environ, {}, clear=True)
    def test_init_without_env_vars(self):
        """Test initialization without environment variables"""
        api = NeonAPI()
        self.assertIsNone(api.api_key)
        self.assertIsNone(api.project_id)

    def test_headers(self):
        """Test headers generation"""
        expected_headers = {
            "Authorization": "Bearer test_api_key",
            "Content-Type": "application/json"
        }
        self.assertEqual(self.api._headers(), expected_headers)

    @patch('requests.get')
    def test_get_endpoint_host_success(self, mock_get):
        """Test successful endpoint host retrieval"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "endpoints": [
                {
                    "branch_id": "test_branch_id",
                    "type": "read_write",
                    "host": "test.host.com"
                }
            ]
        }
        mock_get.return_value = mock_response

        host = self.api.get_endpoint_host(self.api.project_id, self.test_branch_id)
        self.assertEqual(host, "test.host.com")

    @patch('requests.get')
    def test_get_endpoint_host_no_endpoints(self, mock_get):
        """Test endpoint retrieval when no endpoints exist"""
        mock_response = MagicMock()
        mock_response.json.return_value = {"endpoints": []}
        mock_get.return_value = mock_response

        with self.assertRaises(ValueError) as context:
            self.api.get_endpoint_host(self.api.project_id, self.test_branch_id)
        self.assertIn("No endpoints found", str(context.exception))

    @patch('requests.get')
    def test_get_database_name_and_owner_success(self, mock_get):
        """Test successful database and owner retrieval"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "databases": [
                {
                    "name": "test_db",
                    "owner_name": "test_owner"
                }
            ]
        }
        mock_get.return_value = mock_response

        result = self.api.get_database_name_and_owner(self.api.project_id, self.test_branch_id)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["database"], "test_db")
        self.assertEqual(result[0]["user"], "test_owner")

    @patch('requests.get')
    def test_get_database_owner_password_success(self, mock_get):
        """Test successful password retrieval"""
        mock_response = MagicMock()
        mock_response.json.return_value = {"password": "test_password"}
        mock_get.return_value = mock_response

        password = self.api.get_database_owner_password(
            self.api.project_id, 
            self.test_branch_id, 
            "test_user"
        )
        self.assertEqual(password, "test_password")

    def test_missing_api_key(self):
        """Test behavior when API key is missing"""
        api = NeonAPI()
        api.api_key = None
        api.project_id = "test_project_id"

        with self.assertRaises(ValueError) as context:
            api.get_endpoint_host("test_project_id", "test_branch_id")
        self.assertIn("NEON_API_KEY not set", str(context.exception))

    def test_missing_project_id(self):
        """Test behavior when project ID is missing"""
        api = NeonAPI()
        api.api_key = "test_api_key"
        api.project_id = None

        with self.assertRaises(ValueError) as context:
            api.get_endpoint_host(None, "test_branch_id")
        self.assertIn("NEON_PROJECT_ID not set", str(context.exception))

if __name__ == '__main__':
    unittest.main() 