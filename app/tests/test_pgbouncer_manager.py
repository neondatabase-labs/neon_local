import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
import json
import subprocess
from app.pgbouncer.pgbouncer_manager import PgBouncerManager

class TestPgBouncerManager(unittest.TestCase):
    def setUp(self):
        with patch.dict(os.environ, {
            'NEON_PROJECT_ID': 'test_project_id',
            'BRANCH_ID': 'test_branch_id',
            'DELETE_BRANCH': 'true',
            'VSCODE': 'false'
        }):
            self.pgbouncer_manager = PgBouncerManager()

    @patch('subprocess.run')
    def test_generate_certificates(self, mock_run):
        """Test certificate generation"""
        # Mock file existence check and paths
        with patch('os.path.exists', return_value=False), \
             patch('os.chmod') as mock_chmod, \
             patch('os.remove') as mock_remove:
            self.pgbouncer_manager._generate_certificates()

            # Verify openssl commands were called correctly
            self.assertEqual(mock_run.call_count, 3)
            
            # Check key generation
            key_gen_args = mock_run.call_args_list[0][0][0]
            self.assertEqual(key_gen_args[0], 'openssl')
            self.assertEqual(key_gen_args[1], 'genrsa')
            self.assertEqual(key_gen_args[2], '-out')
            self.assertEqual(key_gen_args[3], self.pgbouncer_manager.key_path)
            
            # Check CSR generation
            csr_gen_args = mock_run.call_args_list[1][0][0]
            self.assertEqual(csr_gen_args[0], 'openssl')
            self.assertEqual(csr_gen_args[1], 'req')
            self.assertEqual(csr_gen_args[2], '-new')
            
            # Check certificate generation
            cert_gen_args = mock_run.call_args_list[2][0][0]
            self.assertEqual(cert_gen_args[0], 'openssl')
            self.assertEqual(cert_gen_args[1], 'x509')
            self.assertEqual(cert_gen_args[2], '-req')

            # Verify permissions were set
            mock_chmod.assert_any_call(self.pgbouncer_manager.key_path, 0o600)
            mock_chmod.assert_any_call(self.pgbouncer_manager.cert_path, 0o644)

            # Verify CSR was cleaned up
            mock_remove.assert_called_once_with('/tmp/server.csr')

    @patch('subprocess.run')
    def test_generate_certificates_existing(self, mock_run):
        """Test certificate generation when certificates already exist"""
        # Mock file existence check
        with patch('os.path.exists', return_value=True):
            self.pgbouncer_manager._generate_certificates()
            mock_run.assert_not_called()

    @patch('app.neon.NeonAPI.get_database_name_and_owner')
    @patch('app.neon.NeonAPI.get_branch_connection_info')
    @patch('app.pgbouncer.pgbouncer_manager.NeonAPI')
    @patch('app.neon.requests')
    def test_prepare_config_with_branch_id(self, mock_requests, mock_neon_api, mock_get_branch_connection_info, mock_get_database_name_and_owner):
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
        with patch('builtins.open', mock_open(read_data='[databases]\n[pgbouncer]')):
            with patch('app.pgbouncer.pgbouncer_manager.PgBouncerManager._generate_certificates'):
                self.pgbouncer_manager.prepare_config()
        mock_get_branch_connection_info.assert_called_once_with(self.pgbouncer_manager.project_id, self.pgbouncer_manager.branch_id)

    @patch('app.neon.NeonAPI.fetch_or_create_branch')
    @patch('app.neon.NeonAPI.get_database_name_and_owner')
    @patch('app.neon.NeonAPI.get_branch_connection_info')
    @patch('app.pgbouncer.pgbouncer_manager.NeonAPI')
    @patch('app.neon.requests')
    def test_prepare_config_with_parent_branch(self, mock_requests, mock_neon_api, mock_get_branch_connection_info, mock_get_database_name_and_owner, mock_fetch_or_create_branch):
        """Test config preparation with parent branch"""
        self.pgbouncer_manager.branch_id = None
        self.pgbouncer_manager.parent_branch_id = 'parent_branch_id'

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
        with patch('builtins.open', mock_open(read_data='[databases]\n[pgbouncer]')):
            with patch('app.pgbouncer.pgbouncer_manager.PgBouncerManager._generate_certificates'):
                self.pgbouncer_manager.prepare_config()
        mock_fetch_or_create_branch.assert_called_once()

    @patch('subprocess.Popen')
    def test_start_process(self, mock_popen):
        """Test process start"""
        # Mock file operations
        with patch('builtins.open', mock_open(read_data='[databases]\n[pgbouncer]')):
            with patch('app.pgbouncer.pgbouncer_manager.PgBouncerManager.prepare_config'):
                self.pgbouncer_manager.start_process()

        # Verify PgBouncer was started correctly
        mock_popen.assert_called_once()
        args = mock_popen.call_args[0][0]
        self.assertEqual(args[0], '/usr/bin/pgbouncer')
        self.assertEqual(args[1], '/etc/pgbouncer/pgbouncer.ini')

    @patch('subprocess.Popen')
    def test_stop_process(self, mock_popen):
        """Test process stop"""
        # Create a new instance for each test
        pgbouncer_manager = PgBouncerManager()
        pgbouncer_manager.project_id = 'test_project_id'
        pgbouncer_manager.branch_id = 'test_branch_id'
        
        # Mock process
        mock_process = MagicMock()
        pgbouncer_manager.pgbouncer_process = mock_process
        
        # Test stop
        pgbouncer_manager.stop_process()
        
        # Verify process was stopped
        mock_process.terminate.assert_called_once()
        mock_process.wait.assert_called_once()

    def test_write_pgbouncer_config(self):
        """Test PgBouncer configuration generation"""
        test_databases = [{
            'database': 'test_db',
            'user': 'test_user',
            'password': 'test_pass',
            'host': 'test.host.com'
        }]

        template_content = """
[databases]

[pgbouncer]
pool_mode = transaction
listen_port = 5432
listen_addr = *
auth_type = md5
"""
        expected_config = """
[databases]
test_db=user=test_user password=test_pass host=test.host.com port=5432 dbname=test_db
*=user=test_user password=test_pass host=test.host.com port=5432 dbname=test_db

[pgbouncer]
pool_mode = transaction
listen_port = 5432
listen_addr = *
auth_type = md5
"""

        # Mock file operations
        with patch('builtins.open', mock_open(read_data=template_content)) as mock_file:
            self.pgbouncer_manager._write_pgbouncer_config(test_databases)
            
            # Verify config was written correctly
            mock_file.assert_called_with('/etc/pgbouncer/pgbouncer.ini', 'w')
            written_content = mock_file().write.call_args[0][0]
            self.assertEqual(written_content.strip(), expected_config.strip())

if __name__ == '__main__':
    unittest.main() 