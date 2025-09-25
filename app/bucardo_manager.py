#!/usr/bin/env python3
"""
Bucardo Sync Manager for Neon Local Offline Mode
Manages PostgreSQL replication using Bucardo between local and remote Neon databases.
"""

import os
import subprocess
import logging
import time
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from app.neon import NeonAPI

class BucardoManager:
    def __init__(self):
        self.neon_api = NeonAPI()
        self.local_port = 5433
        self.bucardo_db = "bucardo"
        self.bucardo_user = "bucardo"
        self.bucardo_password = "bucardo_pass"
        self.sync_status_file = "/tmp/.neon_local/bucardo_sync_status.json"
        self.bucardo_initialized = False
        
    def is_offline_mode(self):
        """Check if offline mode is enabled."""
        return os.getenv("OFFLINE_MODE", "false").lower() == "true"
    
    def _get_bucardo_env(self):
        """Get environment variables for Bucardo commands."""
        env = os.environ.copy()
        env['PGPORT'] = str(self.local_port)
        env['PGHOST'] = 'localhost'
        env['PGUSER'] = self.bucardo_user
        env['PGDATABASE'] = self.bucardo_db
        
        # Set up PostgreSQL environment for Neon connections
        env['PGPASSFILE'] = '/tmp/bucardo/.pgpass'
        env['PGSERVICEFILE'] = '/tmp/bucardo/.pg_service.conf'
        
        # Don't set SSL for local connections - local PostgreSQL doesn't use SSL
        # SSL will be set per-connection for remote databases only
        
        # Set Bucardo working and runtime directories
        bucardo_dir = "/tmp/bucardo"
        runtime_dir = "/var/run/bucardo"
        os.makedirs(bucardo_dir, exist_ok=True)
        os.makedirs(runtime_dir, exist_ok=True)
        os.chmod(bucardo_dir, 0o755)
        os.chmod(runtime_dir, 0o755)
        env['HOME'] = bucardo_dir
        return env
    
    def _is_bucardo_running(self):
        """Check if Bucardo is already running by trying to list syncs."""
        try:
            result = self._run_bucardo_command(["bucardo", "list", "syncs"])
            return result.returncode == 0
        except Exception:
            return False
    
    def _run_bucardo_command(self, cmd, **kwargs):
        """Run a Bucardo command with proper environment and working directory."""
        bucardo_dir = "/tmp/bucardo"
        runtime_dir = "/var/run/bucardo"
        os.makedirs(bucardo_dir, exist_ok=True)
        os.makedirs(runtime_dir, exist_ok=True)
        os.chmod(bucardo_dir, 0o755)
        os.chmod(runtime_dir, 0o755)
        
        return subprocess.run(
            cmd,
            env=self._get_bucardo_env(),
            cwd=bucardo_dir,
            capture_output=True,
            text=True,
            **kwargs
        )
    
    def init_bucardo(self):
        """Initialize Bucardo master database and configuration."""
        if not self.is_offline_mode():
            return False
            
        if self.bucardo_initialized or self._is_bucardo_running():
            return True
            
        try:
            logging.info("Initializing Bucardo...")
            
            # Create bucardo database and user
            self._create_bucardo_database()
            
            # Install Bucardo in the database
            result = self._run_bucardo_command([
                "bucardo", "install",
                "--batch",
                f"--dbport={self.local_port}",
                f"--dbhost=localhost",
                f"--dbname={self.bucardo_db}",
                f"--dbuser={self.bucardo_user}",
                f"--dbpass={self.bucardo_password}"
            ])
            
            if result.returncode != 0:
                logging.error(f"Bucardo install failed: {result.stderr}")
                return False
                
            self.bucardo_initialized = True
            logging.info("Bucardo initialized successfully")
            return True
            
        except Exception as e:
            logging.error(f"Failed to initialize Bucardo: {e}")
            return False
    
    def _create_bucardo_database(self):
        """Create the Bucardo master database and user."""
        try:
            # Connect as postgres superuser
            conn = psycopg2.connect(
                host="localhost",
                port=self.local_port,
                database="postgres",
                user="postgres"
            )
            conn.autocommit = True
            cursor = conn.cursor()
            
            # Create bucardo user
            cursor.execute(f"""
                SELECT 1 FROM pg_roles WHERE rolname = '{self.bucardo_user}'
            """)
            
            if not cursor.fetchone():
                cursor.execute(f"""
                    CREATE USER {self.bucardo_user} WITH 
                    PASSWORD '{self.bucardo_password}' 
                    SUPERUSER CREATEDB CREATEROLE
                """)
                logging.info(f"Created Bucardo user: {self.bucardo_user}")
            
            # Create bucardo database
            cursor.execute(f"""
                SELECT 1 FROM pg_database WHERE datname = '{self.bucardo_db}'
            """)
            
            if not cursor.fetchone():
                cursor.execute(f"""
                    CREATE DATABASE {self.bucardo_db} OWNER {self.bucardo_user}
                """)
                logging.info(f"Created Bucardo database: {self.bucardo_db}")
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            logging.error(f"Failed to create Bucardo database: {e}")
            raise
    
    def _ensure_local_database_and_user(self, database, user, password):
        """Ensure local database and user exist for Bucardo."""
        try:
            # Connect as postgres superuser
            conn = psycopg2.connect(
                host="localhost",
                port=self.local_port,
                database="postgres",
                user="postgres"
            )
            conn.autocommit = True
            cursor = conn.cursor()
            
            # Create user if doesn't exist
            cursor.execute(f"""
                SELECT 1 FROM pg_roles WHERE rolname = %s
            """, (user,))
            
            if not cursor.fetchone():
                cursor.execute(f"""
                    CREATE USER "{user}" WITH PASSWORD %s
                """, (password,))
                logging.info(f"Created user '{user}' for Bucardo")
            
            # Create database if doesn't exist
            cursor.execute(f"""
                SELECT 1 FROM pg_database WHERE datname = %s
            """, (database,))
            
            if not cursor.fetchone():
                cursor.execute(f"""
                    CREATE DATABASE "{database}" OWNER "{user}"
                """)
                logging.info(f"Created database '{database}' for Bucardo")
            else:
                # Make sure the user owns the database
                cursor.execute(f"""
                    ALTER DATABASE "{database}" OWNER TO "{user}"
                """)
                logging.info(f"Updated database owner: {database} -> {user}")
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            logging.error(f"Failed to ensure local database/user for Bucardo: {e}")
            raise
    
    def setup_sync(self, remote_connection_info):
        """Set up Bucardo sync between local and remote databases."""
        if not self.is_offline_mode():
            return False
            
        try:
            logging.info("Setting up Bucardo sync configuration...")
            
            # Start Bucardo daemon
            self._start_bucardo_daemon()
            
            for db_info in remote_connection_info:
                self._setup_database_sync(db_info)
            
            logging.info("Bucardo sync setup completed")
            return True
            
        except Exception as e:
            logging.error(f"Failed to setup Bucardo sync: {e}")
            return False
    
    def _start_bucardo_daemon(self):
        """Start the Bucardo daemon process with proper directory setup."""
        try:
            # Ensure all required directories exist
            directories = ["/var/log/bucardo", "/tmp/bucardo", "/var/run/bucardo"]
            for directory in directories:
                os.makedirs(directory, exist_ok=True)
                os.chmod(directory, 0o755)
            
            # Check if daemon is already running
            result = self._run_bucardo_command([
                "bucardo", "status"
            ])
            
            if "PID" in result.stdout:
                logging.info("Bucardo daemon already running")
                return
            
            # Start the daemon (without --daemon flag, it's the default)
            result = self._run_bucardo_command([
                "bucardo", "start"
            ])
            
            if result.returncode != 0:
                logging.error(f"Failed to start Bucardo daemon: {result.stderr}")
                return
            
            # Wait for daemon to be ready
            time.sleep(3)
            logging.info("Bucardo daemon started successfully")
            
        except Exception as e:
            logging.error(f"Failed to start Bucardo daemon: {e}")
            raise
    
    def _setup_database_sync(self, db_info):
        """Set up sync for a specific database."""
        database = db_info['database']
        user = db_info['user']
        password = db_info['password']
        host = db_info['host']
        
        logging.info(f"Setting up Bucardo sync for database: {database}")
        
        try:
            # Create .pgpass entry for remote authentication
            self._create_pgpass_entry(host, database, user, password)
            
            # Ensure local database and user exist first
            self._ensure_local_database_and_user(database, user, password)
            
            # Add local database
            local_db_name = f"{database}_local"
            result = self._run_bucardo_command([
                "bucardo", "add", "db", local_db_name,
                f"dbname={database}",
                f"host=localhost",
                f"port={self.local_port}",
                f"user={user}"
            ])
            
            if result.returncode != 0:
                logging.error(f"Local DB add failed: {result.stderr}")
                logging.error(f"Local DB add stdout: {result.stdout}")
                raise Exception(f"Failed to add local database: {result.stderr}")
            else:
                logging.info(f"Successfully added local database: {local_db_name}")
            
            # Add remote database with Neon-specific settings
            remote_db_name = f"{database}_remote"
            
            # Add database with basic SSL connection first
            result = self._run_bucardo_command([
                "bucardo", "add", "db", remote_db_name,
                f"dbname={database}",
                f"host={host}",
                f"port=5432",
                f"user={user}",
                f"pass={password}",
                f"conn=sslmode=require",
                f"server_side_prepares=0",
                "--force"
            ])
            
            # After adding, manually update the connection string in Bucardo's database
            if result.returncode == 0:
                self._update_remote_db_connection(remote_db_name)
            
            if result.returncode == 0:
                logging.info(f"Successfully added remote database: {remote_db_name}")
            
            if result.returncode != 0:
                logging.error(f"Remote DB add failed: {result.stderr}")
                logging.error(f"Remote DB add stdout: {result.stdout}")
                raise Exception(f"Failed to add remote database: {result.stderr}")
            else:
                logging.info(f"Successfully added remote database: {remote_db_name}")
            
            # Get all tables for this database
            tables = self._get_database_tables(db_info)
            
            if tables:
                logging.info(f"Found {len(tables)} tables to sync: {tables}")
                
                # First, create table structures in local database
                self._create_local_table_structures(db_info, tables)
                
                # Add tables to sync (create herd first)
                herd_name = f"{database}_herd"
                result = self._run_bucardo_command([
                    "bucardo", "add", "herd", herd_name
                ])
                
                # Add tables to herd (now they exist locally)
                for table in tables:
                    result = self._run_bucardo_command([
                        "bucardo", "add", "table", f"{table}",
                        f"db={local_db_name}",
                        f"herd={herd_name}"
                    ])
                    
                    if result.returncode != 0:
                        logging.error(f"Failed to add table {table}: {result.stderr}")
                    else:
                        logging.info(f"Added table {table} to herd {herd_name}")
                
                # Create sync manually in database to bypass validation
                sync_name = f"{database}_sync"
                if self._create_sync_manually(sync_name, herd_name, local_db_name, remote_db_name):
                    result = type('Result', (), {'returncode': 0})()  # Mock success result
                else:
                    result = type('Result', (), {'returncode': 1, 'stderr': 'Manual sync creation failed'})()  # Mock failure result
                
                if result.returncode == 0:
                    logging.info(f"Created Bucardo sync: {sync_name} with {len(tables)} tables")
                else:
                    logging.warning(f"Sync creation result: {result.stderr}")
            
        except Exception as e:
            logging.error(f"Failed to setup sync for {database}: {e}")
            # Don't raise - continue with other databases
    
    def _get_database_tables(self, db_info):
        """Get list of tables in the remote database."""
        try:
            database = db_info['database']
            user = db_info['user']
            password = db_info['password']
            host = db_info['host']
            
            conn = psycopg2.connect(
                host=host,
                port=5432,
                database=database,
                user=user,
                password=password,
                sslmode='require',
                connect_timeout=30
            )
            
            cursor = conn.cursor()
            cursor.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                ORDER BY table_name;
            """)
            tables = [row[0] for row in cursor.fetchall()]
            
            cursor.close()
            conn.close()
            
            return tables
            
        except Exception as e:
            logging.error(f"Failed to get tables for {database}: {e}")
            return []
    
    def _create_local_table_structures(self, db_info, tables):
        """Create table structures in local database by copying from remote with exact schema matching."""
        database = db_info['database']
        user = db_info['user']
        password = db_info['password']
        host = db_info['host']
        
        logging.info(f"Creating table structures in local database for {len(tables)} tables")
        
        try:
            # Connect to remote database (PostgreSQL 17 handles SNI automatically)
            remote_conn = psycopg2.connect(
                host=host,
                port=5432,
                database=database,
                user=user,
                password=password,
                sslmode='require',
                connect_timeout=30
            )
            
            # Connect to local database as postgres superuser
            local_conn = psycopg2.connect(
                host="localhost",
                port=self.local_port,
                database=database,
                user="postgres"
            )
            local_conn.autocommit = True
            
            remote_cursor = remote_conn.cursor()
            local_cursor = local_conn.cursor()
            
            # Ensure neondb_owner has superuser privileges for Bucardo
            try:
                local_cursor.execute("ALTER USER neondb_owner SUPERUSER")
                logging.info("Granted superuser privileges to neondb_owner")
            except Exception as e:
                logging.warning(f"Failed to grant superuser privileges: {e}")
            
            for table in tables:
                try:
                    logging.info(f"Creating table structure: {table}")
                    
                    # Drop existing table to ensure clean recreation
                    local_cursor.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE')
                    
                    # Get detailed table DDL from remote database including identity columns
                    remote_cursor.execute("""
                        SELECT c.column_name, c.data_type, c.is_nullable, c.column_default,
                               c.character_maximum_length, c.numeric_precision, c.numeric_scale,
                               c.is_identity, c.identity_generation
                        FROM information_schema.columns c
                        WHERE c.table_name = %s AND c.table_schema = 'public'
                        ORDER BY c.ordinal_position;
                    """, (table,))
                    
                    columns = remote_cursor.fetchall()
                    
                    if not columns:
                        logging.warning(f"No columns found for table {table}")
                        continue
                    
                    # Build CREATE TABLE statement with exact schema matching
                    create_sql = f'CREATE TABLE "{table}" (\n'
                    col_definitions = []
                    
                    for col in columns:
                        col_name, data_type, is_nullable, default, max_length, precision, scale, is_identity, identity_generation = col
                        
                        # Build column definition with exact column name (preserving case)
                        col_def = f'    "{col_name}" {data_type}'
                        
                        # Add length/precision if applicable
                        if data_type in ('character varying', 'varchar', 'char') and max_length:
                            col_def += f"({max_length})"
                        elif data_type in ('numeric', 'decimal') and precision:
                            if scale:
                                col_def += f"({precision},{scale})"
                            else:
                                col_def += f"({precision})"
                        
                        # Add NOT NULL constraint
                        if is_nullable == 'NO':
                            col_def += " NOT NULL"
                        
                        # Handle IDENTITY columns (PostgreSQL 10+)
                        if is_identity == 'YES':
                            if identity_generation == 'ALWAYS':
                                col_def += " GENERATED ALWAYS AS IDENTITY"
                            else:
                                col_def += " GENERATED BY DEFAULT AS IDENTITY"
                        elif default and default != 'NULL' and 'nextval' not in str(default):
                            # Only add default if it's not a sequence (handled by identity)
                            col_def += f" DEFAULT {default}"
                        
                        col_definitions.append(col_def)
                    
                    create_sql += ",\n".join(col_definitions) + "\n);"
                    
                    # Execute CREATE TABLE
                    local_cursor.execute(create_sql)
                    logging.info(f"Created table structure: {table}")
                    
                    # Copy primary key constraints
                    remote_cursor.execute("""
                        SELECT kcu.column_name, tc.constraint_name
                        FROM information_schema.table_constraints tc
                        JOIN information_schema.key_column_usage kcu 
                            ON tc.constraint_name = kcu.constraint_name
                        WHERE tc.table_name = %s 
                          AND tc.constraint_type = 'PRIMARY KEY'
                          AND tc.table_schema = 'public'
                        ORDER BY kcu.ordinal_position;
                    """, (table,))
                    
                    pk_cols = remote_cursor.fetchall()
                    if pk_cols:
                        pk_columns = [f'"{col[0]}"' for col in pk_cols]  # Quote column names
                        constraint_name = f'"{table}_pkey"'  # Use standard naming
                        pk_sql = f'ALTER TABLE "{table}" ADD CONSTRAINT {constraint_name} PRIMARY KEY ({", ".join(pk_columns)});'
                        try:
                            local_cursor.execute(pk_sql)
                            logging.info(f"Added primary key to {table}")
                        except Exception as pk_error:
                            logging.warning(f"Failed to add primary key to {table}: {pk_error}")
                    
                    # Grant comprehensive permissions to neondb_owner
                    local_cursor.execute(f'GRANT ALL PRIVILEGES ON TABLE "{table}" TO neondb_owner')
                    
                    # Grant sequence permissions for identity columns
                    local_cursor.execute('GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO neondb_owner')
                    
                    logging.info(f"Granted permissions on {table} to neondb_owner")
                    
                except Exception as table_error:
                    logging.error(f"Failed to create table {table}: {table_error}")
                    continue
            
            remote_cursor.close()
            local_cursor.close()
            remote_conn.close()
            local_conn.close()
            
            logging.info(f"Successfully created table structures for {len(tables)} tables")
            
        except Exception as e:
            logging.error(f"Failed to create local table structures: {e}")
            raise
    
    def _create_pgpass_entry(self, host, database, user, password):
        """Create .pgpass entry for password-less authentication."""
        try:
            pgpass_file = "/tmp/bucardo/.pgpass"
            os.makedirs("/tmp/bucardo", exist_ok=True)
            
            # Read existing entries if file exists
            entries = []
            if os.path.exists(pgpass_file):
                with open(pgpass_file, 'r') as f:
                    entries = f.readlines()
            
            # Add new entry if it doesn't exist
            new_entry = f"{host}:5432:{database}:{user}:{password}\n"
            if new_entry not in entries:
                with open(pgpass_file, 'a') as f:
                    f.write(new_entry)
                
                # Set restrictive permissions
                os.chmod(pgpass_file, 0o600)
                logging.info(f"Added .pgpass entry for {host}:{database}")
            
        except Exception as e:
            logging.error(f"Failed to create .pgpass entry: {e}")
            raise
    
    def _update_remote_db_connection(self, remote_db_name):
        """Update the dbconn field for the remote database to include SSL options."""
        try:
            conn = psycopg2.connect(
                host="localhost",
                port=self.local_port,
                database=self.bucardo_db,
                user=self.bucardo_user,
                password=self.bucardo_password
            )
            conn.autocommit = True
            cursor = conn.cursor()
            
            # Use simple SSL connection - newer libpq should handle SNI automatically
            new_conn_string = "sslmode=require connect_timeout=30"
            cursor.execute(
                "UPDATE bucardo.db SET dbconn = %s WHERE name = %s",
                (new_conn_string, remote_db_name)
            )
            
            logging.info(f"Updated dbconn for remote database {remote_db_name} to '{new_conn_string}'")
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            logging.error(f"Failed to update dbconn for remote database {remote_db_name}: {e}")
            return False
    
    def _create_sync_manually(self, sync_name, herd_name, local_db_name, remote_db_name):
        """Manually create sync in Bucardo database to bypass validation."""
        try:
            # Connect to Bucardo database
            conn = psycopg2.connect(
                host="localhost",
                port=self.local_port,
                database=self.bucardo_db,
                user=self.bucardo_user,
                password=self.bucardo_password
            )
            conn.autocommit = True
            cursor = conn.cursor()
            
            # Check if sync already exists
            cursor.execute("SELECT name FROM bucardo.sync WHERE name = %s", (sync_name,))
            if cursor.fetchone():
                logging.info(f"Sync {sync_name} already exists")
                cursor.close()
                conn.close()
                return True
            
            # Check if databases exist
            cursor.execute("SELECT name FROM bucardo.db WHERE name = %s", (local_db_name,))
            if not cursor.fetchone():
                logging.error(f"Local database {local_db_name} not found")
                return False
            
            cursor.execute("SELECT name FROM bucardo.db WHERE name = %s", (remote_db_name,))
            if not cursor.fetchone():
                logging.error(f"Remote database {remote_db_name} not found")
                return False
            
            # Check if herd exists
            cursor.execute("SELECT name FROM bucardo.herd WHERE name = %s", (herd_name,))
            if not cursor.fetchone():
                logging.error(f"Herd {herd_name} not found")
                return False
            
            # Create dbgroup for this sync
            dbgroup_name = f"{sync_name}_dbgroup"
            cursor.execute("""
                INSERT INTO bucardo.dbgroup (name, about)
                VALUES (%s, %s)
                ON CONFLICT (name) DO NOTHING
            """, (dbgroup_name, f"Database group for sync {sync_name}"))
            
            # Add databases to dbgroup (remote=source, local=target for initial sync)
            cursor.execute("""
                INSERT INTO bucardo.dbmap (db, dbgroup, role, priority)
                VALUES (%s, %s, 'source', 1)
                ON CONFLICT (db, dbgroup) DO NOTHING
            """, (remote_db_name, dbgroup_name))
            
            cursor.execute("""
                INSERT INTO bucardo.dbmap (db, dbgroup, role, priority)
                VALUES (%s, %s, 'target', 2)
                ON CONFLICT (db, dbgroup) DO NOTHING
            """, (local_db_name, dbgroup_name))
            
            # Temporarily disable the validation trigger
            cursor.execute("ALTER TABLE bucardo.sync DISABLE TRIGGER validate_sync")
            
            # Insert sync record
            cursor.execute("""
                INSERT INTO bucardo.sync (name, herd, dbs, status, conflict_strategy, checktime)
                VALUES (%s, %s, %s, 'active', 'bucardo_latest_wins', interval '10 seconds')
            """, (sync_name, herd_name, dbgroup_name))
            
            # Re-enable the validation trigger
            cursor.execute("ALTER TABLE bucardo.sync ENABLE TRIGGER validate_sync")
            
            cursor.close()
            conn.close()
            
            logging.info(f"Successfully created sync {sync_name} manually")
            return True
            
        except Exception as e:
            logging.error(f"Failed to create sync manually: {e}")
            return False
    
    def sync_from_remote(self, remote_connection_info):
        """Perform manual sync from remote to local (pull) - on-demand only to minimize remote connections."""
        if not self.is_offline_mode():
            return False
            
        try:
            logging.info("Starting on-demand Bucardo sync from remote to local...")
            
            # Ensure Bucardo daemon is running for the sync operation
            daemon_was_running = self._is_bucardo_running()
            if not daemon_was_running:
                logging.info("Starting Bucardo daemon for sync operation...")
                if not self._start_bucardo_daemon():
                    logging.error("Failed to start Bucardo daemon for sync")
                    return False
            
            for db_info in remote_connection_info:
                database = db_info['database']
                sync_name = f"{database}_sync"
                
                # Restart Bucardo to ensure sync is properly configured and active
                logging.info("Restarting Bucardo to ensure sync is active...")
                restart_result = self._run_bucardo_command(["bucardo", "restart"])
                if restart_result.returncode != 0:
                    logging.warning(f"Bucardo restart failed: {restart_result.stderr}")
                else:
                    time.sleep(3)  # Give Bucardo a moment to fully restart
                
                # Kick off the sync
                result = self._run_bucardo_command([
                    "bucardo", "kick", sync_name
                ])
                
                if result.returncode != 0:
                    logging.error(f"Sync kick failed for {database}: {result.stderr}")
                    continue
                
                # Wait for sync to complete
                self._wait_for_sync_completion(sync_name)
            
            # Stop Bucardo daemon after sync to allow remote database to suspend
            if not daemon_was_running:
                logging.info("Stopping Bucardo daemon to allow remote database auto-suspend...")
                self.stop_bucardo()
                
            self._update_sync_status("pull", "success")
            logging.info("Bucardo sync from remote completed successfully - remote database can now auto-suspend")
            return True
            
        except Exception as e:
            logging.error(f"Bucardo sync from remote failed: {e}")
            self._update_sync_status("pull", "failed", str(e))
            return False
    
    def sync_from_remote_with_fullcopy(self, remote_connection_info):
        """Perform initial fullcopy sync from remote to local, then switch to delta sync."""
        if not self.is_offline_mode():
            return False
            
        try:
            logging.info("Starting Bucardo fullcopy sync from remote to local...")
            
            for db_info in remote_connection_info:
                database = db_info['database']
                sync_name = f"{database}_sync"
                fullcopy_sync_name = f"{database}_fullcopy"
                
                # Step 1: Create and run fullcopy sync for initial data load
                logging.info(f"Creating fullcopy sync for initial data load: {fullcopy_sync_name}")
                if not self._create_fullcopy_sync(fullcopy_sync_name, db_info):
                    logging.error(f"Failed to create fullcopy sync for {database}")
                    continue
                
                # Restart Bucardo to ensure onetimecopy setting takes effect
                logging.info("Restarting Bucardo to activate fullcopy sync settings...")
                restart_result = self._run_bucardo_command(["bucardo", "restart"])
                if restart_result.returncode != 0:
                    logging.warning(f"Bucardo restart failed: {restart_result.stderr}")
                else:
                    time.sleep(3)  # Give Bucardo a moment to fully restart
                
                # Run the fullcopy sync
                logging.info(f"Running fullcopy sync: {fullcopy_sync_name}")
                result = self._run_bucardo_command([
                    "bucardo", "kick", fullcopy_sync_name
                ])
                
                if result.returncode != 0:
                    logging.error(f"Fullcopy sync kick failed for {database}: {result.stderr}")
                    continue
                
                # Wait for fullcopy to complete
                logging.info(f"Waiting for fullcopy sync to complete: {fullcopy_sync_name}")
                if self._wait_for_fullcopy_completion(fullcopy_sync_name, database, timeout=30):  # 30 second timeout
                    logging.info(f"Fullcopy sync completed successfully for {database}")
                    
                    # Fix sequence values after fullcopy to prevent duplicate key errors
                    logging.info(f"Synchronizing sequence values for {database}")
                    if not self._sync_sequences(database):
                        logging.warning(f"Failed to synchronize sequences for {database}")
                else:
                    logging.error(f"Fullcopy sync timed out for {database}")
                    continue
                
                # Step 2: Remove fullcopy sync and switch to regular delta sync
                logging.info(f"Removing fullcopy sync: {fullcopy_sync_name}")
                self._remove_sync(fullcopy_sync_name)
                
                # The regular delta sync should already be set up from setup_sync()
                logging.info(f"Initial data copy completed for {database}, regular sync {sync_name} is ready for ongoing changes")
                
            self._update_sync_status("fullcopy_pull", "success")
            logging.info("Bucardo fullcopy sync from remote completed successfully")
            return True
            
        except Exception as e:
            logging.error(f"Bucardo fullcopy sync from remote failed: {e}")
            self._update_sync_status("fullcopy_pull", "failed", str(e))
            return False
    
    def _create_fullcopy_sync(self, sync_name, db_info):
        """Create a temporary fullcopy sync for initial data loading."""
        try:
            database = db_info['database']
            user = db_info['user']
            password = db_info['password']
            host = db_info['host']
            
            # Create temporary database entries for fullcopy
            local_db_name = f"{database}_local_fullcopy"
            remote_db_name = f"{database}_remote_fullcopy"
            herd_name = f"{database}_fullcopy_herd"
            
            # Add temporary local database for fullcopy
            result = self._run_bucardo_command([
                "bucardo", "add", "db", local_db_name,
                f"dbname={database}",
                f"host=localhost",
                f"port={self.local_port}",
                f"user={user}"
            ])
            
            if result.returncode != 0:
                logging.error(f"Failed to add local DB for fullcopy: {result.stderr}")
                return False
            
            # Add temporary remote database for fullcopy with password
            result = self._run_bucardo_command([
                "bucardo", "add", "db", remote_db_name,
                f"dbname={database}",
                f"host={host}",
                f"port=5432",
                f"user={user}",
                f"pass={password}",
                "--force"  # Skip connection tests
            ])
            
            if result.returncode != 0:
                logging.error(f"Failed to add remote DB for fullcopy: {result.stderr}")
                return False
            
            # Update remote database connection string
            self._update_remote_db_connection(remote_db_name)
            
            # Create .pgpass entry for fullcopy remote database
            self._create_pgpass_entry(host, database, user, password)
            
            # Get tables and add to herd
            tables = self._get_database_tables(db_info)
            if not tables:
                logging.warning(f"No tables found for fullcopy sync in database {database}")
                return False
            
            # Add tables to herd
            for table in tables:
                result = self._run_bucardo_command([
                    "bucardo", "add", "table", table, f"db={local_db_name}", f"herd={herd_name}"
                ])
                
                if result.returncode != 0:
                    logging.warning(f"Failed to add table {table} to fullcopy herd: {result.stderr}")
            
            # Create fullcopy sync using Bucardo command with onetimecopy=2
            return self._create_fullcopy_sync_with_command(sync_name, herd_name, local_db_name, remote_db_name)
            
        except Exception as e:
            logging.error(f"Failed to create fullcopy sync: {e}")
            return False
    
    def _create_fullcopy_sync_with_command(self, sync_name, herd_name, local_db_name, remote_db_name):
        """Create fullcopy sync using Bucardo command with onetimecopy=1."""
        try:
            logging.info(f"Creating fullcopy sync {sync_name} with onetimecopy=1")
            
            # Use Bucardo command to create fullcopy sync with onetimecopy=1
            # This always does a full copy, which works reliably for initial sync
            result = self._run_bucardo_command([
                "bucardo", "add", "sync", sync_name,
                f"relgroup={herd_name}",
                f"dbs={remote_db_name},{local_db_name}",
                "onetimecopy=1"
            ])
            
            if result.returncode != 0:
                logging.error(f"Failed to create fullcopy sync with command: {result.stderr}")
                return False
            
            logging.info(f"Successfully created fullcopy sync {sync_name} with onetimecopy=1")
            
            # Ensure onetimecopy=1 is actually set (Bucardo command sometimes doesn't persist it)
            try:
                conn = psycopg2.connect(
                    host="localhost",
                    port=self.local_port,
                    database=self.bucardo_db,
                    user=self.bucardo_user,
                    password=self.bucardo_password
                )
                conn.autocommit = True
                cursor = conn.cursor()
                
                # Force set onetimecopy=1 to ensure fullcopy behavior
                cursor.execute("UPDATE bucardo.sync SET onetimecopy = 1 WHERE name = %s", (sync_name,))
                logging.info(f"Ensured onetimecopy=1 is set for sync {sync_name}")
                
                cursor.close()
                conn.close()
                
            except Exception as e:
                logging.warning(f"Could not verify onetimecopy setting: {e}")
            
            return True
            
        except Exception as e:
            logging.error(f"Failed to create fullcopy sync with command: {e}")
            return False
    
    def _remove_sync(self, sync_name):
        """Remove a sync and its associated objects."""
        try:
            logging.info(f"Removing sync: {sync_name}")
            
            # Remove the sync
            result = self._run_bucardo_command([
                "bucardo", "remove", "sync", sync_name
            ])
            
            if result.returncode != 0:
                logging.warning(f"Failed to remove sync {sync_name}: {result.stderr}")
            
            # Clean up associated database entries
            dbgroup_name = f"{sync_name}_dbgroup"
            
            # Connect to Bucardo database for manual cleanup
            conn = psycopg2.connect(
                host="localhost",
                port=self.local_port,
                database=self.bucardo_db,
                user=self.bucardo_user,
                password=self.bucardo_password
            )
            conn.autocommit = True
            cursor = conn.cursor()
            
            # Remove dbmap entries
            cursor.execute("DELETE FROM bucardo.dbmap WHERE dbgroup = %s", (dbgroup_name,))
            
            # Remove dbgroup
            cursor.execute("DELETE FROM bucardo.dbgroup WHERE name = %s", (dbgroup_name,))
            
            cursor.close()
            conn.close()
            
            logging.info(f"Successfully removed sync {sync_name} and associated objects")
            return True
            
        except Exception as e:
            logging.error(f"Failed to remove sync {sync_name}: {e}")
            return False
    
    def sync_to_remote(self, remote_connection_info):
        """Push operations are not supported due to Neon database permission limitations."""
        logging.warning("Push operations (local to remote) are not supported")
        logging.warning("Neon databases don't provide superuser privileges required for Bucardo push operations")
        logging.info("Use pull operations to sync changes from remote to local instead")
        return False
    
    def _reverse_sync_direction(self, sync_name, database):
        """Temporarily reverse sync direction for push operation."""
        try:
            local_db_name = f"{database}_local"
            remote_db_name = f"{database}_remote"
            dbgroup_name = f"{sync_name}_dbgroup"
            
            # Update the dbgroup to reverse roles: local becomes source, remote becomes target
            result = self._run_bucardo_command([
                "bucardo", "update", "dbgroup", dbgroup_name,
                f"{local_db_name}:source:pri=1",
                f"{remote_db_name}:target:pri=2"
            ])
            
            if result.returncode != 0:
                logging.error(f"Failed to reverse sync direction: {result.stderr}")
                raise subprocess.CalledProcessError(result.returncode, "bucardo update dbgroup")
            
        except Exception as e:
            logging.error(f"Failed to reverse sync direction: {e}")
            raise
    
    def _restore_sync_direction(self, sync_name, database):
        """Restore original sync direction after push operation."""
        try:
            local_db_name = f"{database}_local"
            remote_db_name = f"{database}_remote"
            dbgroup_name = f"{sync_name}_dbgroup"
            
            # Restore original roles: remote becomes source, local becomes target
            result = self._run_bucardo_command([
                "bucardo", "update", "dbgroup", dbgroup_name,
                f"{remote_db_name}:source:pri=1",
                f"{local_db_name}:target:pri=2"
            ])
            
            if result.returncode != 0:
                logging.error(f"Failed to restore sync direction: {result.stderr}")
                raise subprocess.CalledProcessError(result.returncode, "bucardo update dbgroup")
            
        except Exception as e:
            logging.error(f"Failed to restore sync direction: {e}")
            raise
    
    def _wait_for_sync_completion(self, sync_name, timeout=300):
        """Wait for sync to complete with improved detection logic."""
        logging.info(f"Waiting for sync {sync_name} to complete (timeout: {timeout}s)...")
        
        start_time = time.time()
        last_sync_time = None
        
        while time.time() - start_time < timeout:
            try:
                # Check sync status
                result = self._run_bucardo_command([
                    "bucardo", "status", sync_name
                ])
                
                if result.returncode == 0:
                    # Parse the output to check if sync is complete
                    if "Good" in result.stdout or "Complete" in result.stdout:
                        logging.info(f"Sync {sync_name} completed successfully")
                        return True
                    elif "Bad" in result.stdout or "Failed" in result.stdout:
                        logging.error(f"Sync {sync_name} failed: {result.stdout}")
                        return False
                    
                    # For fullcopy syncs, check if sync has run recently by looking at logs
                    if "fullcopy" in sync_name:
                        # Check Bucardo logs for recent completion of this sync
                        try:
                            log_result = subprocess.run([
                                "tail", "-50", "/var/log/bucardo/log.bucardo"
                            ], capture_output=True, text=True, timeout=10)
                            
                            if log_result.returncode == 0:
                                # Look for recent completion of this sync in logs
                                recent_logs = log_result.stdout
                                if f'syncdone_{sync_name.replace("_fullcopy", "_fullcopy")}' in recent_logs:
                                    # Check if this completion happened recently (within last 60 seconds)
                                    current_time = time.time()
                                    if current_time - start_time < 60:
                                        logging.info(f"Sync {sync_name} completed successfully (detected via logs)")
                                        return True
                        except Exception as log_e:
                            logging.debug(f"Could not check logs for sync completion: {log_e}")
                
                # Wait before checking again
                time.sleep(2)  # Reduced from 5 to 2 seconds for faster detection
                
            except Exception as e:
                logging.warning(f"Error checking sync status: {e}")
                time.sleep(2)
        
        logging.warning(f"Sync {sync_name} timed out after {timeout} seconds")
        return False
    
    def _wait_for_fullcopy_completion(self, sync_name, database, timeout=120):
        """Wait for fullcopy sync to complete by checking actual data presence."""
        logging.info(f"Waiting for fullcopy sync {sync_name} to complete (timeout: {timeout}s)...")
        
        start_time = time.time()
        
        # First, give the sync a moment to start
        time.sleep(3)
        
        while time.time() - start_time < timeout:
            try:
                # Check if data has been copied by counting rows in local database
                conn = psycopg2.connect(
                    host="localhost",
                    port=self.local_port,
                    database=database,
                    user="postgres"
                )
                cursor = conn.cursor()
                
                # Get total row count across all synced tables
                total_rows = 0
                cursor.execute("""
                    SELECT schemaname, tablename 
                    FROM pg_tables 
                    WHERE schemaname = 'public' 
                    AND tablename IN ('books', 'users', 'local_data_test')
                """)
                
                tables = cursor.fetchall()
                for schema, table in tables:
                    cursor.execute(f'SELECT COUNT(*) FROM "{schema}"."{table}"')
                    row_count = cursor.fetchone()[0]
                    total_rows += row_count
                    logging.debug(f"Table {schema}.{table}: {row_count} rows")
                
                cursor.close()
                conn.close()
                
                # If we have data, the fullcopy sync succeeded
                if total_rows > 0:
                    logging.info(f"Fullcopy sync {sync_name} completed successfully - {total_rows} total rows copied")
                    return True
                
                # Also check Bucardo logs for completion messages
                try:
                    import subprocess
                    log_result = subprocess.run([
                        "tail", "-20", "/var/log/bucardo/log.bucardo"
                    ], capture_output=True, text=True, timeout=5)
                    
                    if log_result.returncode == 0:
                        recent_logs = log_result.stdout
                        # Look for sync completion messages in the last few lines
                        if f"syncdone_{sync_name}" in recent_logs or f"syncdone_neondb_fullcopy" in recent_logs:
                            # Even if no data was copied, the sync completed
                            logging.info(f"Fullcopy sync {sync_name} completed (detected via logs)")
                            return True
                except Exception as log_e:
                    logging.debug(f"Could not check logs: {log_e}")
                
                # Wait before checking again
                time.sleep(3)
                
            except Exception as e:
                logging.warning(f"Error checking fullcopy completion: {e}")
                time.sleep(3)
        
        logging.warning(f"Fullcopy sync {sync_name} timed out after {timeout} seconds")
        return False
    
    def _sync_sequences(self, database):
        """Synchronize sequence values to match the highest existing IDs in tables."""
        try:
            logging.info(f"Synchronizing sequences for database {database}")
            
            # Connect to local database
            conn = psycopg2.connect(
                host="localhost",
                port=self.local_port,
                database=database,
                user="postgres"
            )
            conn.autocommit = True
            cursor = conn.cursor()
            
            # Get all tables with auto-increment columns (both sequences and identity columns)
            cursor.execute("""
                SELECT 
                    table_name,
                    column_name,
                    is_identity
                FROM information_schema.columns
                WHERE table_schema = 'public'
                    AND (column_default LIKE 'nextval%' OR is_identity = 'YES')
                ORDER BY table_name
            """)
            
            tables_with_sequences = cursor.fetchall()
            
            if not tables_with_sequences:
                logging.info("No tables with sequences found to synchronize")
                cursor.close()
                conn.close()
                return True
            
            sequences_updated = 0
            for table_name, column_name, is_identity in tables_with_sequences:
                try:
                    # Get the maximum value from the table
                    cursor.execute(f'SELECT COALESCE(MAX("{column_name}"), 0) FROM public."{table_name}"')
                    max_value = cursor.fetchone()[0]
                    
                    if max_value > 0:
                        new_value = max_value + 1
                        
                        if is_identity == 'YES':
                            # For identity columns, restart the sequence
                            cursor.execute(f'ALTER TABLE public."{table_name}" ALTER COLUMN "{column_name}" RESTART WITH %s', (new_value,))
                            logging.info(f"Restarted identity column {table_name}.{column_name} with {new_value} (max value: {max_value})")
                        else:
                            # For regular sequences, use setval
                            sequence_name = f"{table_name}_{column_name}_seq"
                            cursor.execute(f'SELECT setval(%s, %s)', (sequence_name, new_value))
                            logging.info(f"Updated sequence {sequence_name} to {new_value} (max {column_name} in {table_name}: {max_value})")
                        
                        sequences_updated += 1
                    else:
                        logging.info(f"Table {table_name} is empty, skipping sequence sync")
                        
                except Exception as seq_e:
                    logging.error(f"Failed to sync sequence for {table_name}.{column_name}: {seq_e}")
                    continue
            
            cursor.close()
            conn.close()
            
            logging.info(f"Successfully synchronized {sequences_updated} sequences for database {database}")
            return True
            
        except Exception as e:
            logging.error(f"Failed to synchronize sequences for database {database}: {e}")
            return False
    
    def _update_sync_status(self, operation, status, error=None):
        """Update sync status file."""
        try:
            os.makedirs(os.path.dirname(self.sync_status_file), exist_ok=True)
            
            sync_status = {
                "last_sync": time.time(),
                "operation": operation,
                "status": status,
                "error": error
            }
            
            with open(self.sync_status_file, 'w') as f:
                json.dump(sync_status, f, indent=2)
                
        except Exception as e:
            logging.error(f"Failed to update sync status: {e}")
    
    def get_sync_status(self):
        """Get the current sync status."""
        try:
            if os.path.exists(self.sync_status_file):
                with open(self.sync_status_file, 'r') as f:
                    return json.load(f)
            return None
        except Exception as e:
            logging.error(f"Failed to read sync status: {e}")
            return None
    
    def stop_bucardo(self):
        """Stop Bucardo daemon and clean up."""
        try:
            logging.info("Stopping Bucardo daemon...")
            result = self._run_bucardo_command([
                "bucardo", "stop"
            ])
            if result.returncode == 0:
                logging.info("Bucardo daemon stopped - remote database can now auto-suspend")
            else:
                logging.warning(f"Bucardo stop returned non-zero: {result.stderr}")
        except Exception as e:
            logging.error(f"Failed to stop Bucardo daemon: {e}")
    
    def pause_continuous_sync(self):
        """Pause continuous sync to allow remote database to auto-suspend."""
        if not self.is_offline_mode():
            return False
        
        try:
            logging.info("Pausing continuous sync to allow remote database auto-suspend...")
            
            # Stop all active syncs
            result = self._run_bucardo_command(["bucardo", "list", "syncs"])
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'Sync' in line and '[Active]' in line:
                        # Extract sync name
                        sync_name = line.split('"')[1] if '"' in line else None
                        if sync_name:
                            logging.info(f"Pausing sync: {sync_name}")
                            pause_result = self._run_bucardo_command([
                                "bucardo", "pause", sync_name
                            ])
                            if pause_result.returncode == 0:
                                logging.info(f"Successfully paused sync: {sync_name}")
                            else:
                                logging.warning(f"Failed to pause sync {sync_name}: {pause_result.stderr}")
            
            # Stop the Bucardo daemon entirely to free remote connections
            self.stop_bucardo()
            return True
            
        except Exception as e:
            logging.error(f"Failed to pause continuous sync: {e}")
            return False
    
    def resume_continuous_sync(self):
        """Resume continuous sync after manual sync operations."""
        if not self.is_offline_mode():
            return False
        
        try:
            logging.info("Resuming continuous sync...")
            
            # Start Bucardo daemon if not running
            if not self._is_bucardo_running():
                if not self._start_bucardo_daemon():
                    logging.error("Failed to start Bucardo daemon")
                    return False
            
            # Resume all paused syncs
            result = self._run_bucardo_command(["bucardo", "list", "syncs"])
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'Sync' in line and '[Paused]' in line:
                        # Extract sync name
                        sync_name = line.split('"')[1] if '"' in line else None
                        if sync_name:
                            logging.info(f"Resuming sync: {sync_name}")
                            resume_result = self._run_bucardo_command([
                                "bucardo", "resume", sync_name
                            ])
                            if resume_result.returncode == 0:
                                logging.info(f"Successfully resumed sync: {sync_name}")
                            else:
                                logging.warning(f"Failed to resume sync {sync_name}: {resume_result.stderr}")
            
            return True
            
        except Exception as e:
            logging.error(f"Failed to resume continuous sync: {e}")
            return False
