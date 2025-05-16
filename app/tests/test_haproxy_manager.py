import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
import json
import subprocess
from app.haproxy.haproxy_manager import HAProxyManager

class TestHAProxyManager(unittest.TestCase):
    def setUp(self):
        with patch.dict(os.environ, {
            'NEON_PROJECT_ID': 'test_project_id',
            'BRANCH_ID': 'test_branch_id',
            'DELETE_BRANCH': 'true',
            'VSCODE': 'false'
        }):
            self.haproxy_manager = HAProxyManager()

    @patch('os.path.exists', return_value=True)
    @patch('app.neon.NeonAPI.get_database_name_and_owner')
    @patch('app.neon.NeonAPI.get_branch_connection_info')
    @patch('app.haproxy.haproxy_manager.NeonAPI')
    @patch('app.neon.requests')
    def test_prepare_config_with_branch_id(self, mock_requests, mock_neon_api, mock_get_branch_connection_info, mock_get_database_name_and_owner, mock_exists):
        """Test config preparation with branch ID"""
        # Patch return values
        mock_get_branch_connection_info.return_value = [{
            'database': 'test_db',
            'user': 'test_user',
            'password': 'test_pass',
            'host': 'test.host.com'
        }]
        mock_get_database_name_and_owner.return_value = [{
            'name': 'test_db',
            'owner_name': 'test_user'
        }]

        # Mock file operations
        with patch('builtins.open', mock_open(read_data='frontend\nbackend http_backend')):
            self.haproxy_manager.prepare_config()
        mock_get_branch_connection_info.assert_called_once_with(self.haproxy_manager.project_id, self.haproxy_manager.branch_id)

    @patch('app.neon.NeonAPI.fetch_or_create_branch')
    @patch('os.path.exists', return_value=True)
    @patch('app.neon.NeonAPI.get_database_name_and_owner')
    @patch('app.neon.NeonAPI.get_branch_connection_info')
    @patch('app.haproxy.haproxy_manager.NeonAPI')
    @patch('app.neon.requests')
    def test_prepare_config_with_parent_branch(self, mock_requests, mock_neon_api, mock_get_branch_connection_info, mock_get_database_name_and_owner, mock_exists, mock_fetch_or_create_branch):
        """Test config preparation with parent branch"""
        self.haproxy_manager.branch_id = None
        self.haproxy_manager.parent_branch_id = 'parent_branch_id'

        # Patch return values
        mock_get_branch_connection_info.return_value = [{
            'database': 'test_db',
            'user': 'test_user',
            'password': 'test_pass',
            'host': 'test.host.com'
        }]
        mock_get_database_name_and_owner.return_value = [{
            'name': 'test_db',
            'owner_name': 'test_user'
        }]
        mock_fetch_or_create_branch.return_value = (
            [{'database': 'test_db', 'user': 'test_user', 'password': 'test_pass', 'host': 'test.host.com'}],
            {'test_branch': {'branch_id': 'test_branch_id'}}
        )

        # Mock file operations
        with patch('builtins.open', mock_open(read_data='frontend\nbackend http_backend')):
            self.haproxy_manager.prepare_config()
        mock_fetch_or_create_branch.assert_called_once()

    @patch('subprocess.Popen')
    def test_start_process(self, mock_popen):
        """Test process start"""
        # Mock file operations
        with patch('builtins.open', mock_open(read_data='frontend\nbackend http_backend')):
            with patch('app.haproxy.haproxy_manager.HAProxyManager.prepare_config'):
                self.haproxy_manager.start_process()

        # Verify HAProxy was started correctly
        mock_popen.assert_called_once()
        args = mock_popen.call_args[0][0]
        self.assertEqual(args[0], 'haproxy')
        self.assertEqual(args[1], '-f')
        self.assertEqual(args[2], '/tmp/haproxy.cfg')

    @patch('subprocess.Popen')
    def test_stop_process(self, mock_popen):
        """Test process stop"""
        # Create a new instance for each test
        haproxy_manager = HAProxyManager()
        haproxy_manager.project_id = 'test_project_id'
        haproxy_manager.branch_id = 'test_branch_id'
        
        # Mock process
        mock_process = MagicMock()
        haproxy_manager.haproxy_process = mock_process
        
        # Test stop
        haproxy_manager.stop_process()
        
        # Verify process was stopped
        mock_process.terminate.assert_called_once()
        mock_process.wait.assert_called_once()

    def test_write_haproxy_config(self):
        """Test HAProxy configuration generation"""
        test_databases = [{
            'database': 'test_db',
            'user': 'test_user',
            'password': 'test_pass',
            'host': 'test.host.com'
        }]

        template_content = """frontend http_frontend
    bind *:80
    mode http

backend http_backend
    mode http"""

        expected_config = """frontend http_frontend
    bind *:80
    mode http
    acl is_sql path_beg /sql
    acl is_test_db path_beg /test_db
    acl is_test_db_connection hdr(Neon-Connection-String) -m reg -i test_db
    use_backend backend_test_db if is_test_db or is_sql is_test_db_connection
    default_backend backend_test_db

backend backend_test_db
    server ws_server1 test.host.com:443 ssl verify none sni str(test.host.com) check
    http-request set-header Neon-Connection-String \"postgresql://test_user:test_pass@test.host.com/test_db?sslmode=require\"
    http-request set-header Host test.host.com"""

        # Mock file operations and path
        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data=template_content)) as mock_file:
            self.haproxy_manager._write_haproxy_config(test_databases)

            # Verify config was written correctly
            mock_file.assert_called_with('/tmp/haproxy.cfg', 'w')
            written_content = mock_file().write.call_args[0][0]
            # Normalize whitespace for comparison
            def normalize(s):
                return '\n'.join(line.rstrip() for line in s.strip().splitlines() if line.strip())
            self.assertEqual(normalize(written_content), normalize(expected_config))

    def test_write_haproxy_config_missing_template(self):
        """Test error handling for missing template file"""
        with patch('os.path.exists', return_value=False):
            with self.assertRaises(FileNotFoundError):
                self.haproxy_manager._write_haproxy_config([])

if __name__ == '__main__':
    unittest.main() 