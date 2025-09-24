#!/usr/bin/env python3
"""
Neon Local Sync CLI
Command-line interface for syncing data between local and remote databases in offline mode.
"""

import sys
import json
import argparse
from app.offline_manager import OfflineManager
from app.neon import NeonAPI
import os

def get_remote_connection_info():
    """Get remote connection information from environment variables."""
    try:
        neon_api = NeonAPI()
        project_id = os.getenv("NEON_PROJECT_ID")
        branch_id = os.getenv("BRANCH_ID")
        
        if not project_id:
            raise ValueError("NEON_PROJECT_ID environment variable not set")
        
        if branch_id:
            return neon_api.get_branch_connection_info(project_id, branch_id)
        else:
            # Try to get from state file
            from app.process_manager import ProcessManager
            pm = ProcessManager()
            state = pm._get_neon_branch()
            current_branch = pm._get_git_branch()
            
            if current_branch and current_branch in state:
                branch_id = state[current_branch]["branch_id"]
                return neon_api.get_branch_connection_info(project_id, branch_id)
            else:
                raise ValueError("No branch ID found in environment or state")
                
    except Exception as e:
        print(f"Error getting remote connection info: {e}")
        return None

def cmd_pull(args):
    """Pull data from remote to local database."""
    if not os.getenv("OFFLINE_MODE", "false").lower() == "true":
        print("Error: Not in offline mode. Set OFFLINE_MODE=true to use sync commands.")
        return 1
    
    print("Syncing data from remote to local database...")
    
    offline_manager = OfflineManager()
    remote_info = get_remote_connection_info()
    
    if not remote_info:
        print("Error: Could not get remote connection information")
        return 1
    
    if offline_manager.sync_from_remote(remote_info):
        print("✓ Sync from remote completed successfully")
        return 0
    else:
        print("✗ Sync from remote failed")
        return 1

def cmd_push(args):
    """Push data from local to remote database."""
    if not os.getenv("OFFLINE_MODE", "false").lower() == "true":
        print("Error: Not in offline mode. Set OFFLINE_MODE=true to use sync commands.")
        return 1
    
    print("Syncing data from local to remote database...")
    
    offline_manager = OfflineManager()
    remote_info = get_remote_connection_info()
    
    if not remote_info:
        print("Error: Could not get remote connection information")
        return 1
    
    if offline_manager.sync_to_remote(remote_info):
        print("✓ Sync to remote completed successfully")
        return 0
    else:
        print("✗ Sync to remote failed")
        return 1

def cmd_status(args):
    """Show sync status."""
    offline_manager = OfflineManager()
    
    if not offline_manager.is_offline_mode():
        print("Offline mode: Disabled")
        print("Sync is only available when OFFLINE_MODE=true")
        return 0
    
    print("Offline mode: Enabled")
    
    status = offline_manager.get_sync_status()
    
    if status.get("status") == "never_synced":
        print("Sync status: Never synced")
    else:
        import time
        last_sync = status.get("last_sync", 0)
        last_sync_str = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(last_sync))
        
        print(f"Last sync: {last_sync_str}")
        print(f"Operation: {status.get('operation', 'unknown')}")
        print(f"Status: {status.get('status', 'unknown')}")
        
        if status.get("error"):
            print(f"Error: {status.get('error')}")
    
    return 0

def cmd_init(args):
    """Initialize offline mode (setup local PostgreSQL)."""
    offline_manager = OfflineManager()
    
    if not offline_manager.is_offline_mode():
        print("Error: OFFLINE_MODE environment variable must be set to 'true'")
        return 1
    
    print("Initializing offline mode...")
    
    # Initialize local PostgreSQL
    if not offline_manager.init_local_postgres():
        print("✗ Failed to initialize local PostgreSQL")
        return 1
    
    print("✓ Local PostgreSQL initialized")
    
    # Start local PostgreSQL
    if not offline_manager.start_local_postgres():
        print("✗ Failed to start local PostgreSQL")
        return 1
    
    print("✓ Local PostgreSQL started")
    
    # Initial sync from remote
    remote_info = get_remote_connection_info()
    if remote_info:
        print("Performing initial sync from remote...")
        if offline_manager.sync_from_remote(remote_info):
            print("✓ Initial sync completed successfully")
        else:
            print("⚠ Initial sync failed, but offline mode is ready")
    else:
        print("⚠ Could not get remote connection info for initial sync")
    
    print("✓ Offline mode initialization complete")
    return 0

def main():
    parser = argparse.ArgumentParser(
        description="Neon Local Sync CLI - Sync data between local and remote databases"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Pull command
    pull_parser = subparsers.add_parser("pull", help="Pull data from remote to local")
    pull_parser.set_defaults(func=cmd_pull)
    
    # Push command  
    push_parser = subparsers.add_parser("push", help="Push data from local to remote")
    push_parser.set_defaults(func=cmd_push)
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Show sync status")
    status_parser.set_defaults(func=cmd_status)
    
    # Init command
    init_parser = subparsers.add_parser("init", help="Initialize offline mode")
    init_parser.set_defaults(func=cmd_init)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\nOperation cancelled")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
