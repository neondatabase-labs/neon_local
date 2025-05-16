import pytest
import os
from unittest.mock import patch

@pytest.fixture(autouse=True)
def mock_env_vars():
    """Automatically mock environment variables for all tests"""
    with patch.dict(os.environ, {
        'NEON_API_KEY': 'test_api_key',
        'NEON_PROJECT_ID': 'test_project_id',
        'BRANCH_ID': 'test_branch_id',
        'DELETE_BRANCH': 'true',
        'VSCODE': 'false'
    }):
        yield

@pytest.fixture
def mock_requests():
    """Mock requests for API calls"""
    with patch('requests.get') as mock_get, \
         patch('requests.delete') as mock_delete:
        yield {
            'get': mock_get,
            'delete': mock_delete
        }

@pytest.fixture
def mock_file_operations():
    """Mock file operations"""
    with patch('builtins.open') as mock_open:
        yield mock_open 