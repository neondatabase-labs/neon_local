import os
import subprocess
import psycopg2
import logging
import time
import json
from app.neon import NeonAPI
from app.bucardo_manager import BucardoManager

class OfflineManager:
    def __init__(self):
        self.neon_api = NeonAPI()
        self.postgres_process = None
        self.local_port = 5433  # Local PostgreSQL port (internal)
        self.data_dir = "/var/lib/postgresql/17/main"  # Use existing cluster
        self.log_file = "/var/log/postgresql.log"
        self.sync_status_file = "/var/lib/postgresql/sync_status.json"
        self.bucardo_manager = BucardoManager()
        
    def is_offline_mode(self):
        """Check if offline mode is enabled."""
        return os.getenv("OFFLINE_MODE", "false").lower() == "true"
    
    def init_local_postgres(self):
        """Initialize local PostgreSQL instance."""
        if not self.is_offline_mode():
            return False
            
        logging.info("Initializing local PostgreSQL for offline mode...")
        
        try:
            # Check if data directory already exists and is initialized
            if os.path.exists(os.path.join(self.data_dir, "PG_VERSION")):
                logging.info("Local PostgreSQL cluster already exists")
                # Update configuration for our needs
                self._write_postgresql_conf()
                return True
            
            # If for some reason it doesn't exist, initialize it
            logging.info("Initializing PostgreSQL data directory...")
            subprocess.run([
                "sudo", "-u", "postgres", 
                "/usr/lib/postgresql/17/bin/initdb",
                "-D", self.data_dir,
                "--auth-local=trust",
                "--auth-host=md5"
            ], check=True, capture_output=True, text=True)
            
            # Create postgresql.conf with our settings
            self._write_postgresql_conf()
            
            logging.info("Local PostgreSQL initialized successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to initialize PostgreSQL: {e}")
            return False
    
    def _write_postgresql_conf(self):
        """Write PostgreSQL configuration file."""
        # Copy the sample config files
        sample_config = "/usr/share/postgresql/17/postgresql.conf.sample"
        sample_hba = "/usr/share/postgresql/17/pg_hba.conf.sample"
        sample_ident = "/usr/share/postgresql/17/pg_ident.conf.sample"
        
        config_path = os.path.join(self.data_dir, "postgresql.conf")
        hba_path = os.path.join(self.data_dir, "pg_hba.conf")
        ident_path = os.path.join(self.data_dir, "pg_ident.conf")
        
        # Copy sample configs
        subprocess.run(["cp", sample_config, config_path], check=True)
        subprocess.run(["cp", sample_hba, hba_path], check=True)
        subprocess.run(["cp", sample_ident, ident_path], check=True)
        
        # Append our custom settings to postgresql.conf
        custom_config = f"""

# Neon Local offline mode settings
port = {self.local_port}
listen_addresses = 'localhost'
unix_socket_directories = '/var/run/postgresql'
max_connections = 100

# Logging
log_destination = 'stderr'
logging_collector = on
log_directory = '/var/log'
log_filename = 'postgresql.log'

# Security
ssl = off
password_encryption = md5
"""
        
        with open(config_path, "a") as f:
            f.write(custom_config)
        
        # Create a simple pg_hba.conf for local access
        hba_config = """# TYPE  DATABASE        USER            ADDRESS                 METHOD

# "local" is for Unix domain socket connections only
local   all             all                                     trust
# IPv4 local connections:
host    all             all             127.0.0.1/32            trust
host    all             all             ::1/128                 trust
"""
        
        with open(hba_path, "w") as f:
            f.write(hba_config)
        
        # Set proper ownership
        subprocess.run(["chown", "postgres:postgres", config_path, hba_path, ident_path], check=True)
    
    def start_local_postgres(self):
        """Start local PostgreSQL instance."""
        if not self.is_offline_mode():
            return None
            
        logging.info("Starting local PostgreSQL...")
        
        try:
            # Start PostgreSQL using pg_ctl
            result = subprocess.run([
                "sudo", "-u", "postgres",
                "/usr/lib/postgresql/17/bin/pg_ctl",
                "start",
                "-D", self.data_dir,
                "-l", self.log_file,
                "-o", f"-p {self.local_port}"
            ], capture_output=True, text=True, check=True)
            
            logging.info("PostgreSQL start command completed")
            
            # Wait for PostgreSQL to be ready
            self._wait_for_postgres_ready()
            
            # Create the default database and user
            self._create_default_database()
            
            logging.info(f"Local PostgreSQL started on port {self.local_port}")
            return True
            
        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to start PostgreSQL: {e}")
            logging.error(f"stdout: {e.stdout}")
            logging.error(f"stderr: {e.stderr}")
            return None
        except Exception as e:
            logging.error(f"Failed to start PostgreSQL: {e}")
            return None
    
    def stop_local_postgres(self):
        """Stop local PostgreSQL instance and Bucardo."""
        if not self.postgres_process:
            return
            
        logging.info("Stopping Bucardo and local PostgreSQL...")
        
        try:
            # Stop Bucardo first
            self.bucardo_manager.stop_bucardo()
            
            subprocess.run([
                "sudo", "-u", "postgres",
                "/usr/lib/postgresql/17/bin/pg_ctl",
                "stop",
                "-D", self.data_dir,
                "-m", "fast"
            ], check=True, timeout=30)
            
            self.postgres_process = None
            logging.info("Local PostgreSQL stopped")
            
        except Exception as e:
            logging.error(f"Failed to stop PostgreSQL gracefully: {e}")
            if self.postgres_process:
                self.postgres_process.kill()
                self.postgres_process = None
    
    def _wait_for_postgres_ready(self, max_wait=30):
        """Wait for PostgreSQL to be ready to accept connections."""
        logging.info("Waiting for PostgreSQL to be ready...")
        
        for i in range(max_wait):
            try:
                # Try to connect
                conn = psycopg2.connect(
                    host="localhost",
                    port=self.local_port,
                    user="postgres",
                    database="postgres"
                )
                conn.close()
                logging.info(f"PostgreSQL ready (took {i+1}s)")
                return True
            except psycopg2.OperationalError:
                time.sleep(1)
        
        raise Exception(f"PostgreSQL not ready after {max_wait} seconds")
    
    def _create_default_database(self):
        """Create the default database and user for Neon Local offline mode."""
        try:
            # Create the neondb database
            result = subprocess.run([
                "sudo", "-u", "postgres",
                "psql", "-h", "localhost", "-p", str(self.local_port),
                "-d", "postgres", "-c", "CREATE DATABASE IF NOT EXISTS neondb;"
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                # Try without IF NOT EXISTS for older PostgreSQL versions
                result = subprocess.run([
                    "sudo", "-u", "postgres",
                    "psql", "-h", "localhost", "-p", str(self.local_port),
                    "-d", "postgres", "-c", "CREATE DATABASE neondb;"
                ], capture_output=True, text=True)
            
            # Create the neondb_owner user
            result = subprocess.run([
                "sudo", "-u", "postgres", 
                "psql", "-h", "localhost", "-p", str(self.local_port),
                "-d", "postgres", "-c", "CREATE USER neondb_owner WITH PASSWORD 'local_password';"
            ], capture_output=True, text=True)
            
            # Grant privileges to the user
            subprocess.run([
                "sudo", "-u", "postgres",
                "psql", "-h", "localhost", "-p", str(self.local_port),
                "-d", "postgres", "-c", "GRANT ALL PRIVILEGES ON DATABASE neondb TO neondb_owner;"
            ], capture_output=True, text=True)
            
            logging.info("Default database and user created successfully")
            
        except Exception as e:
            logging.error(f"Error creating database/user: {e}")
            # Try to create them anyway, they might already exist
            pass
    
    def sync_from_remote(self, remote_connection_info):
        """Sync data from remote Neon database to local PostgreSQL using Bucardo."""
        if not self.is_offline_mode():
            logging.info("Not in offline mode, skipping sync")
            return False
            
        logging.info("Starting Bucardo sync from remote to local...")
        
        # For manual sync operations, use the regular sync method (not fullcopy)
        # This assumes Bucardo is already initialized and configured from container startup
        return self.bucardo_manager.sync_from_remote(remote_connection_info)
    
    def sync_from_remote_initial(self, remote_connection_info):
        """Perform initial sync during container startup - includes setup and fullcopy."""
        if not self.is_offline_mode():
            logging.info("Not in offline mode, skipping sync")
            return False
            
        logging.info("Starting Bucardo initial fullcopy sync from remote to local...")
        
        # Initialize Bucardo if not already done
        if not self.bucardo_manager.init_bucardo():
            logging.error("Failed to initialize Bucardo")
            return False
        
        # Pre-create local databases and users BEFORE setup_sync
        for db_info in remote_connection_info:
            database = db_info['database']
            user = db_info['user']
            password = db_info['password']
            
            logging.info(f"Pre-creating local database and user for {database}")
            try:
                self.bucardo_manager._ensure_local_database_and_user(database, user, password)
                logging.info(f"Successfully created database {database} and user {user}")
            except Exception as e:
                logging.error(f"Failed to create database {database}: {e}")
                return False
        
        # Setup sync configuration
        if not self.bucardo_manager.setup_sync(remote_connection_info):
            logging.error("Failed to setup Bucardo sync")
            return False
        
        # Perform initial fullcopy sync, then switch to regular delta sync
        initial_sync_success = self.bucardo_manager.sync_from_remote_with_fullcopy(remote_connection_info)
        
        # Pause continuous sync after initial setup to allow remote database auto-suspend
        if initial_sync_success:
            logging.info("Pausing continuous sync after initial setup to allow remote database auto-suspend...")
            self.bucardo_manager.pause_continuous_sync()
        
        return initial_sync_success
    
    def sync_to_remote(self, remote_connection_info):
        """Push operations are not supported due to Neon database permission limitations."""
        logging.warning("Push operations (local to remote) are not supported")
        logging.warning("Neon databases don't provide superuser privileges required for Bucardo push operations")
        logging.info("Use pull operations to sync changes from remote to local instead")
        return False
    
    def _update_sync_status(self, operation, status, error=None):
        """Update sync status file."""
        try:
            sync_status = {
                "last_sync": time.time(),
                "operation": operation,
                "status": status,
                "error": error
            }
            
            os.makedirs(os.path.dirname(self.sync_status_file), exist_ok=True)
            with open(self.sync_status_file, 'w') as f:
                json.dump(sync_status, f, indent=2)
                
        except Exception as e:
            logging.error(f"Failed to update sync status: {e}")
    
    def get_sync_status(self):
        """Get current sync status."""
        return self.bucardo_manager.get_sync_status()
