import unittest
from unittest.mock import patch, MagicMock
import os
import json
import threading
import time
from app.process_manager import ProcessManager

class TestProcessManager(unittest.TestCase):
    def setUp(self):
        with patch.dict(os.environ, {
            'NEON_PROJECT_ID': 'test_project_id',
            'BRANCH_ID': 'test_branch_id',
            'DELETE_BRANCH': 'true',
            'VSCODE': 'false'
        }):
            self.process_manager = ProcessManager()

    def test_init_with_required_env_vars(self):
        """Test initialization with required environment variables"""
        self.assertEqual(self.process_manager.project_id, 'test_project_id')
        self.assertEqual(self.process_manager.branch_id, 'test_branch_id')
        self.assertTrue(self.process_manager.delete_branch)
        self.assertFalse(self.process_manager.vscode)

    def test_init_without_project_id(self):
        """Test initialization without required project ID"""
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError) as context:
                ProcessManager()
            self.assertIn("NEON_PROJECT_ID environment variable is required", str(context.exception))

    def test_calculate_file_hash(self):
        """Test file hash calculation"""
        # Create a temporary test file
        test_file = "test_file.txt"
        test_content = "test content"
        
        with open(test_file, "w") as f:
            f.write(test_content)
        
        try:
            hash_value = self.process_manager.calculate_file_hash(test_file)
            self.assertIsNotNone(hash_value)
            self.assertEqual(len(hash_value), 64)  # SHA-256 hash length
        finally:
            if os.path.exists(test_file):
                os.remove(test_file)

    def test_calculate_file_hash_nonexistent(self):
        """Test file hash calculation for nonexistent file"""
        hash_value = self.process_manager.calculate_file_hash("nonexistent_file.txt")
        self.assertIsNone(hash_value)

    @patch('app.process_manager.ProcessManager.start_process')
    @patch('app.process_manager.ProcessManager.stop_process')
    def test_reload(self, mock_stop, mock_start):
        """Test reload functionality"""
        self.process_manager.reload()
        mock_stop.assert_called_once()
        mock_start.assert_called_once()

    @patch('builtins.open', new_callable=MagicMock)
    def test_get_git_branch(self, mock_open):
        """Test git branch retrieval"""
        mock_open.return_value.__enter__.return_value.read.return_value = "ref: refs/heads/test-branch"
        branch = self.process_manager._get_git_branch()
        self.assertEqual(branch, "test-branch")

    @patch('builtins.open', new_callable=MagicMock)
    def test_get_neon_branch(self, mock_open):
        """Test neon branch state retrieval"""
        test_state = {"branch1": {"branch_id": "id1"}}
        mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(test_state)
        state = self.process_manager._get_neon_branch()
        self.assertEqual(state, test_state)

    @patch('builtins.open', new_callable=MagicMock)
    def test_write_neon_branch(self, mock_open):
        """Test neon branch state writing"""
        test_state = {
            "branch1": [
                {
                    "database": "test_db",
                    "user": "test_user",
                    "branch_id": "test_branch_id"
                }
            ]
        }
        self.process_manager._write_neon_branch(test_state)
        mock_open.assert_called_once()

    def test_cleanup(self):
        """Test cleanup functionality"""
        self.process_manager.watcher_thread = MagicMock()
        self.process_manager.reloader_thread = MagicMock()
        
        self.process_manager.cleanup()
        
        self.assertTrue(self.process_manager.shutdown_event.is_set())
        self.process_manager.watcher_thread.join.assert_called_once()
        self.process_manager.reloader_thread.join.assert_called_once()

if __name__ == '__main__':
    unittest.main() 